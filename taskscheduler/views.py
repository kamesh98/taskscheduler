import logging
import traceback

from django.db import transaction
from django.http import JsonResponse
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from taskscheduler.helpers import can_assign_resource, find_earliest_assignment
from taskscheduler.models import Assignments, Project, Resource, Skill, Task
from taskscheduler.serializers import (AssignmentsSerializer, AssignSerializer,
                                       PlanSerializer, ProjectSerializer,
                                       ResourceSerializer, SkillSerializer,
                                       TaskSerializer)

logger = logging.getLogger()


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.save()

        # Set all the task under it to be deleted
        tasks = Task.objects.filter(project=instance)
        assignments = Assignments.objects.filter(task__in=[task.id for task in tasks])
        tasks.update(is_deleted=True)
        # Delete all assignments associated with the tasks
        print(assignments)
        assignments.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.save()

        assignments = Assignments.objects.filter(task=instance.id)
        assignments.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def retrieve(self, request, *args, **kwargs):
        show_assignments = request.GET.get("show_assignments", False)
        response = super().retrieve(request, *args, **kwargs)
        if show_assignments:
            if response.status_code == 200:
                task_data = response.data
                task_id = task_data["id"]
                assignment = Assignments.objects.filter(task=task_id).first()
                if assignment:
                    task_data["assignment"] = assignment.id
                    task_data["assigned_resource"] = assignment.resource.id
        return response


class ResourceViewSet(viewsets.ModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer

    def retrieve(self, request, *args, **kwargs):
        show_assignments = request.GET.get("show_assignments", False)
        response = super().retrieve(request, *args, **kwargs)
        if show_assignments:
            if response.status_code == 200:
                resource = response.data
                resource_id = resource["id"]
                assignments = Assignments.objects.filter(
                    resource=resource_id, status="ASSIGNED"
                )
                assignments_list = []
                for assignment in assignments:
                    assignment_dict = {}
                    assignment_dict["assignment"] = assignment.id
                    assignment_dict["task"] = assignment.task.id
                    assignment_dict["start_date"] = assignment.start_date
                    assignment_dict["end_date"] = assignment.end_date
                    assignments_list.append(assignment_dict)
                resource["assignments"] = assignments_list
        return response


class SkillViewSet(viewsets.ModelViewSet):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer


class PlanCreateView(APIView):
    http_method_names = ["post"]
    serializer_class = PlanSerializer

    def post(self, request, *args, **kwargs):
        serializer = PlanSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    # TODO: Lot of duplicate code make helper function to reduce it
                    planned_assignments = []
                    project_id = serializer.data.get("project_id")
                    if project_id:
                        # Get a list of unfinshed tasks give priority to task with start date and sort by project created time
                        unassigned_tasks = Task.unassigned_objects.filter(
                            project=project_id
                        ).order_by("start_date", "id")
                        for task in unassigned_tasks:
                            (
                                start_date,
                                end_date,
                                resource_id,
                            ) = find_earliest_assignment(task.id)
                            if not start_date or not end_date or not resource_id:
                                transaction.set_rollback(True)
                                logger.warning(
                                    f"Task {task.id} could not be scheduled becasue we have another assignment."
                                )
                                return JsonResponse(
                                    {
                                        "message": f"Task {task.id} could not be scheduled."
                                    },
                                    status=400,
                                )
                            planned_assignment = {
                                "task_id": task.id,
                                "resource_id": resource_id,
                                "start_date": start_date,
                                "end_date": end_date,
                            }
                            existing_assignment = Assignments.objects.filter(
                                task_id=task.id, resource_id=resource_id
                            ).first()
                            if existing_assignment:
                                transaction.set_rollback(True)
                                logger.warning(
                                    "Task {task.id} is already assigned to the resource."
                                )
                                return JsonResponse(
                                    {
                                        "message": f"Task {task.id} is already assigned to the resource."
                                    },
                                    status=400,
                                )
                            assignment = Assignments(
                                task_id=task.id,
                                resource_id=resource_id,
                                start_date=start_date,
                                end_date=end_date,
                                status="ASSIGNED",
                            )
                            assignment.save()
                            planned_assignments.append(planned_assignment)
                        transaction.set_rollback(True)
                        logger.info(
                            "Creating just the plan not the assignment rolling back"
                        )
                        return Response(planned_assignments)
                    else:
                        unassigned_tasks = serializer.data.get("tasks")
                        if unassigned_tasks:
                            for task in unassigned_tasks:
                                task_id = task.get("task_id")
                                resource_id = task.get("resource_id")
                                (
                                    start_date,
                                    end_date,
                                    resource_id,
                                ) = find_earliest_assignment(task_id, resource_id)
                                if not start_date or not end_date or not resource_id:
                                    transaction.set_rollback(True)
                                    logger.warning(
                                        f"Task {task.id} could not be scheduled since the resource was not having a slot."
                                    )
                                    return JsonResponse(
                                        {
                                            "message": f"Task {task.id} could not be scheduled."
                                        },
                                        status=400,
                                    )
                                planned_assignment = {
                                    "task_id": task_id,
                                    "resource_id": resource_id,
                                    "start_date": start_date,
                                    "end_date": end_date,
                                }
                                existing_assignment = Assignments.objects.filter(
                                    task_id=task_id, resource_id=resource_id
                                ).first()
                                if existing_assignment:
                                    transaction.set_rollback(True)
                                    logger.warning(
                                        f"Task {task_id} is already assigned to the resource."
                                    )
                                    return JsonResponse(
                                        {
                                            "message": f"Task {task_id} is already assigned to the resource."
                                        },
                                        status=400,
                                    )
                                assignment = Assignments(
                                    task_id=task_id,
                                    resource_id=resource_id,
                                    start_date=start_date,
                                    end_date=end_date,
                                    status="ASSIGNED",
                                )
                                assignment.save()
                                planned_assignments.append(planned_assignment)
                        transaction.set_rollback(True)
                        logger.info(
                            "Creating just the plan not the assignment rolling back"
                        )
                        return Response(planned_assignments)
            except Exception as e:
                print(traceback.format_exc())
                error_message = str(e)
                error_response = {"message": "Dry run failed", "error": error_message}
                logger.exception("Failed while creating the plan", exc_info=True)
                return Response(error_response, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AssignmentsCreateView(APIView):
    http_method_names = ["post"]
    serializer_class = AssignSerializer

    def post(self, request, *args, **kwargs):
        serializer = AssignSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    planned_assignments = []
                    project_id = serializer.data.get("project_id")
                    if project_id:
                        # Get a list of unfinshed tasks give priority to task with start date and sort by project created time
                        unassigned_tasks = Task.unassigned_objects.filter(
                            project=project_id
                        ).order_by("start_date", "id")
                        for task in unassigned_tasks:
                            (
                                start_date,
                                end_date,
                                resource_id,
                            ) = find_earliest_assignment(task.id)
                            planned_assignment = {
                                "task_id": task.id,
                                "resource_id": resource_id,
                                "start_date": start_date,
                                "end_date": end_date,
                            }
                            if not start_date or not end_date or not resource_id:
                                transaction.set_rollback(True)
                                logger.warning(
                                    f"Task {task.id} could not be scheduled."
                                )
                                return JsonResponse(
                                    {
                                        "message": f"Task {task.id} could not be scheduled."
                                    },
                                    status=400,
                                )
                            existing_assignment = Assignments.objects.filter(
                                task_id=task.id, resource_id=resource_id
                            ).first()
                            if existing_assignment:
                                transaction.set_rollback(True)
                                logger.warning(
                                    f"Task {task.id} is already assigned to the resource."
                                )
                                return JsonResponse(
                                    {
                                        "message": f"Task {task.id} is already assigned to the resource."
                                    },
                                    status=400,
                                )
                            assignment = Assignments(
                                task_id=task.id,
                                resource_id=resource_id,
                                start_date=start_date,
                                end_date=end_date,
                                status="ASSIGNED",
                            )
                            assignment.save()
                            planned_assignments.append(planned_assignment)
                        return Response(planned_assignments)
                    else:
                        unassigned_tasks = serializer.data.get("tasks")
                        if unassigned_tasks:
                            for task in unassigned_tasks:
                                task_id = task.get("task_id")
                                resource_id = task.get("resource_id")
                                start_date = task.get("start_date")
                                end_date = task.get("end_date")
                                if start_date and end_date:
                                    if not can_assign_resource(
                                        resource_id, task_id, start_date, end_date
                                    ):
                                        transaction.set_rollback(True)
                                        logger.warning(
                                            f"Cannot Task {task_id} to the resource {resource_id}"
                                        )
                                        return JsonResponse(
                                            {
                                                "message": f"Cannot Task {task_id} to the resource {resource_id}."
                                            },
                                            status=400,
                                        )
                                else:
                                    (
                                        start_date,
                                        end_date,
                                        resource_id,
                                    ) = find_earliest_assignment(task_id, resource_id)
                                if not start_date or not end_date or not resource_id:
                                    transaction.set_rollback(True)
                                    logger.warning(
                                        f"Task {task.id} could not be scheduled for the given resource."
                                    )
                                    return JsonResponse(
                                        {
                                            "message": f"Task {task.id} could not be scheduled."
                                        },
                                        status=400,
                                    )
                                planned_assignment = {
                                    "task_id": task_id,
                                    "resource_id": resource_id,
                                    "start_date": start_date,
                                    "end_date": end_date,
                                }
                                existing_assignment = Assignments.objects.filter(
                                    task_id=task_id, resource_id=resource_id
                                ).first()
                                if existing_assignment:
                                    transaction.set_rollback(True)
                                    logger.warning(
                                        f"Task {task.id} is already assigned to the resource."
                                    )
                                    return JsonResponse(
                                        {
                                            "message": f"Task {task_id} is already assigned to the resource."
                                        },
                                        status=400,
                                    )
                                assignment = Assignments(
                                    task_id=task_id,
                                    resource_id=resource_id,
                                    start_date=start_date,
                                    end_date=end_date,
                                    status="ASSIGNED",
                                )
                                assignment.save()
                                planned_assignments.append(planned_assignment)
                        return Response(planned_assignments)
            except Exception as e:
                print(traceback.format_exc())
                error_message = str(e)
                error_response = {"message": "Dry run failed", "error": error_message}
                logger.exception("Failed while creating the assignment", exc_info=True)
                return Response(error_response, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AssignmentsViewSet(viewsets.ModelViewSet):
    queryset = Assignments.objects.all()
    serializer_class = AssignmentsSerializer
    http_method_names = ["get", "put", "patch", "delete"]
