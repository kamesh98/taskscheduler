from django.db import models


class ProjectManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class UnfinishedProject(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False, completed=False)


class Project(models.Model):
    name = models.CharField(max_length=100)
    created_date = models.DateField(null=True)
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)
    is_deleted = models.BooleanField(null=True)
    completed = models.BooleanField(null=True)
    completed_date = models.DateField(null=True)

    objects = ProjectManager()
    unfinished = UnfinishedProject()

    class Meta:
        db_table = "project"


class TaskManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class UnassignedTaskManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(is_deleted=False, assignments__isnull=True, completed=False)
        )


class Task(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)
    created_date = models.DateField(null=True)
    skills_required = models.ManyToManyField("Skill")
    estimation = models.IntegerField(null=True)
    is_deleted = models.BooleanField(null=True)
    completed = models.BooleanField(null=True)
    completed_date = models.DateField(null=True)

    objects = TaskManager()
    unassigned_objects = UnassignedTaskManager()

    class Meta:
        db_table = "task"

    @property
    def status(self):
        return self.assignments.status


class Resource(models.Model):
    name = models.CharField(max_length=100)
    skills = models.ManyToManyField("Skill")
    availability_start_date = models.DateField()
    availability_end_date = models.DateField(null=True)

    class Meta:
        db_table = "resource"


class Skill(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "skill"


class Assignments(models.Model):
    STATUS_CHOICES = [
        ("ASSIGNED", "Assigned"),
        ("COMPLETED", "Completed"),
    ]
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="assignments")
    resource = models.ForeignKey(
        Resource, on_delete=models.CASCADE, related_name="assignments"
    )
    start_date = models.DateField(null=False)
    end_date = models.DateField(null=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)

    class Meta:
        db_table = "assignment"
