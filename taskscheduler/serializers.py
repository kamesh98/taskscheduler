import datetime

from django.db.models import Q
from rest_framework import serializers

from taskscheduler.helpers import can_assign_resource
from taskscheduler.models import Assignments, Project, Resource, Skill, Task


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        exclude = ("is_deleted", "created_date", "completed_date")

    def create(self, validated_data):
        validated_data["is_deleted"] = False
        validated_data["created_date"] = datetime.datetime.now()
        # Updating the completed date if it a completed project was created
        if validated_data["completed"]:
            validated_data["completed_date"] = datetime.datetime.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Updating the completed date
        if validated_data["completed"]:
            validated_data["completed_date"] = datetime.datetime.now()
        else:
            validated_data["completed_date"] = None
        return super().update(instance, validated_data)

    def validate_completed(self, value):
        instance = self.instance
        if instance and instance.completed and not value:
            raise serializers.ValidationError(
                "A completed Project cannot be marked as non-completed."
            )

        return value

    def validate_update(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        completed = attrs.get("completed")
        project_id = self.instance.id

        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                "Start date cannot be greater than completion date"
            )

        # Checking if we have any pending tasks under project
        if completed and project_id:
            if not Task.objects.filter(
                (Q(completed=True) | Q(completed__isnull=True)), project=project_id
            ).exists():
                raise serializers.ValidationError(
                    "Project cannot be finsihed before all the taks is ended"
                )

        return attrs

    def validate_create(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")

        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                "Start date cannot be greater than completion date"
            )
        return attrs


class TaskSerializer(serializers.ModelSerializer):
    project = serializers.PrimaryKeyRelatedField(queryset=Project.unfinished.all())

    class Meta:
        model = Task
        exclude = ("is_deleted", "created_date", "completed_date")

    def create(self, validated_data):
        validated_data["is_deleted"] = False
        validated_data["created_date"] = datetime.datetime.now()
        # Updating the completed date if it a completed task was created
        if validated_data["completed"]:
            validated_data["completed_date"] = datetime.datetime.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Updating the completed date
        if "completed" in validated_data and validated_data["completed"]:
            assignment = Assignments.objects.filter(task_id=instance.pk).first()
            if assignment:
                assignment.status = "COMPLETED"
                assignment.save()
        return super().update(instance, validated_data)

    def validate_completed(self, value):
        instance = self.instance
        if instance and instance.completed and not value:
            raise serializers.ValidationError(
                "A completed task cannot be marked as non-completed."
            )

        return value

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")

        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                "Start date cannot be greater than completion date"
            )

        # if we have an estimation we cannot be less than days been start and end dates
        estimation = attrs.get("estimation")
        if (
            estimation
            and start_date
            and end_date
            and estimation > (end_date - start_date).days
        ):
            raise serializers.ValidationError(
                "Project estimation is longer that deadline"
            )

        project = attrs.get("project")
        if project is not None:
            if project.completed is True:
                raise serializers.ValidationError(
                    "Completed project cannot be added a task"
                )

            project_start_date = project.start_date
            project_end_date = project.end_date

            if start_date and project_start_date and start_date > project_start_date:
                raise serializers.ValidationError(
                    "Start date cannot be greater than Project start date"
                )

            if end_date and project_end_date and end_date > project_end_date:
                raise serializers.ValidationError(
                    "End date cannot be greater than Project End date"
                )

        return attrs


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = "__all__"


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = "__all__"


class PlanTaskSerializer(serializers.Serializer):
    task_id = serializers.PrimaryKeyRelatedField(queryset=Task.unassigned_objects.all())
    resource_id = serializers.PrimaryKeyRelatedField(
        queryset=Resource.objects.all(), allow_null=True, default=None
    )


class PlanSerializer(serializers.Serializer):
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.unfinished.all(), allow_null=True, default=None
    )
    tasks = PlanTaskSerializer(many=True, required=False)

    def validate(self, attrs):
        if "project_id" not in attrs and "tasks" not in attrs:
            raise serializers.ValidationError(
                "Either 'project_id' or 'tasks' must be provided."
            )
        project_id = attrs.get("project_id")
        tasks = attrs.get("tasks")
        if project_id is None and tasks is None:
            raise serializers.ValidationError(
                "Either 'project_id' or 'tasks' must be provided."
            )
        if project_id is not None and tasks is not None:
            raise serializers.ValidationError(
                "Only one of 'project_id' or 'tasks' should be provided."
            )
        return attrs


class TaskAssignSerializer(serializers.Serializer):
    task_id = serializers.PrimaryKeyRelatedField(queryset=Task.unassigned_objects.all())
    resource_id = serializers.PrimaryKeyRelatedField(
        queryset=Resource.objects.all(), allow_null=True, default=None
    )
    start_date = serializers.DateTimeField(allow_null=True, required=False)
    end_date = serializers.DateTimeField(allow_null=True, required=False)


class AssignSerializer(serializers.Serializer):
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.unfinished.all(), allow_null=True, default=None
    )
    tasks = TaskAssignSerializer(many=True, required=False)

    def validate(self, attrs):
        if "project_id" not in attrs and "tasks" not in attrs:
            raise serializers.ValidationError(
                "Either 'project_id' or 'tasks' must be provided."
            )
        project_id = attrs.get("project_id")
        tasks = attrs.get("tasks")
        if project_id is None and tasks is None:
            raise serializers.ValidationError(
                "Either 'project_id' or 'tasks' must be provided."
            )
        if project_id is not None and tasks is not None:
            raise serializers.ValidationError(
                "Only one of 'project_id' or 'tasks' should be provided."
            )
        if tasks is not None:
            for task_item in tasks:
                task_id = task_item["task_id"]
                start_date = task_item["start_date"]
                end_date = task_item["end_date"]
                task = Task.objects.get(id=task_id)
                task_start = task.start_date
                task_end = task.end_date
                if start_date and task_start and start_date < task_start:
                    raise serializers.ValidationError(
                        "Assignment must be within the task deadline"
                    )
                if end_date and task_end and end_date > task_end:
                    raise serializers.ValidationError(
                        "Assignment must be within the task deadline"
                    )
                # checking EXOR
                if (task_start is not None) ^ (task_end is not None):
                    raise serializers.ValidationError(
                        "Start and End should be empty or should have both"
                    )
        return attrs


class AssignmentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignments
        fields = "__all__"
        read_only_fields = ("task",)

    def validate_status(self, value):
        instance = self.instance
        if instance and instance.status == "COMPLETED" and value == "ASSIGNED":
            raise serializers.ValidationError(
                "Cannot change status from 'Completed' to 'Unassigned'."
            )
        return value

    def update(self, instance, validated_data):
        if (
            "status" in validated_data
            and instance.status == "ASSIGNED"
            and validated_data["status"] == "COMPLETED"
        ):
            validated_data["end_date"] = validated_data.get(
                "end_date", datetime.datetime.now()
            )

        start_date = validated_data.get("start_date", instance.start_date)
        end_date = validated_data.get("end_date", instance.end_date)
        resource_id = validated_data.get("resource_id", instance.resource_id)

        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                "Invalid dates. Start date cannot be greater than end date."
            )

        if (
            start_date != instance.start_date
            or end_date != instance.end_date
            or resource_id != instance.resource_id
        ):
            if not can_assign_resource(
                resource_id, instance.task_id, start_date, end_date, instance.id
            ):
                raise serializers.ValidationError(
                    "Cannot update 'start_date' or 'end_date'. Resource cannot be re-assigned."
                )
        return super().update(instance, validated_data)
