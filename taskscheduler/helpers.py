import datetime
from datetime import datetime, timedelta

from taskscheduler.models import Assignments, Resource, Task


def find_earliest_assignment(task_id, resource_id=None):
    task = Task.objects.get(id=task_id)
    earliest_assignment_start_date = None
    earliest_assignment_end_date = None
    earliest_resource_id = None

    if resource_id is not None:
        resources = [Resource.objects.filter(id=resource_id)]
    else:
        resources = Resource.objects.all()

    skills_required = task.skills_required.all()
    for skill in skills_required:
        resources = resources.filter(skills=skill)
    if not resources.count() > 0:
        return (
            earliest_assignment_start_date,
            earliest_assignment_end_date,
            earliest_resource_id,
        )

    for resource in resources:
        current_earliest_assignment_start_date = None
        if (
            task.start_date is None
            or resource.availability_start_date <= task.start_date
        ) and (
            task.end_date is None
            or resource.availability_end_date is None
            or resource.availability_end_date >= task.end_date
        ):
            # Get all future assignments for the resource
            future_assignments = Assignments.objects.filter(
                resource=resource,
                end_date__gte=datetime.now().date()
                - timedelta(
                    days=task.estimation
                ),  # Consider existing assignments that end within the estimation period
                status="ASSIGNED",
            ).order_by("start_date")

            # Find the ongoing assignment if any
            ongoing_assignment = future_assignments.filter(
                start_date__lte=datetime.now().date(),
                end_date__gte=datetime.now().date(),
            ).first()

            # Determine the prev_assignment_end_date based on ongoing assignment or today's date
            if ongoing_assignment:
                prev_assignment_end_date = ongoing_assignment.end_date
            else:
                prev_assignment_end_date = datetime.now().date()
            found_gap = False

            if task.start_date is not None:
                prev_assignment_end_date = max(
                    prev_assignment_end_date, task.start_date - timedelta(days=1)
                )

            # Find the earliest assignment date with a gap greater than task estimation
            # This finds if an any gap between the resource assignment where the can take it
            for assignment in future_assignments:
                if assignment.start_date > prev_assignment_end_date + timedelta(
                    days=task.estimation
                ):
                    current_earliest_assignment_start_date = (
                        prev_assignment_end_date + timedelta(days=1)
                    )
                    found_gap = True
                    break
                # Assign the prev_assignment day only if assignment end day is larger than it for future tasks
                if prev_assignment_end_date < assignment.end_date:
                    prev_assignment_end_date = assignment.end_date
                # If the task end date is earlier than the date that resource can take it skip this resource
                if (
                    task.end_date is not None
                    and prev_assignment_end_date >= task.end_date
                ):
                    continue

            if not found_gap:
                current_earliest_assignment_start_date = (
                    prev_assignment_end_date + timedelta(days=1)
                )

            # Check if the current earliest assignment is tomorrow if tomorrow exit becuase we can't find enything sooner
            if current_earliest_assignment_start_date == datetime.today() + timedelta(
                days=1
            ):
                earliest_assignment_start_date = current_earliest_assignment_start_date
                earliest_assignment_end_date = (
                    current_earliest_assignment_start_date
                    + timedelta(days=task.estimation)
                )
                earliest_resource_id = resource.id
                break

            if earliest_assignment_start_date is None or (
                current_earliest_assignment_start_date is not None
                and current_earliest_assignment_start_date
                < earliest_assignment_start_date
            ):
                earliest_assignment_start_date = current_earliest_assignment_start_date
                earliest_assignment_end_date = (
                    current_earliest_assignment_start_date
                    + timedelta(days=task.estimation)
                )
                earliest_resource_id = resource.id

    return (
        earliest_assignment_start_date,
        earliest_assignment_end_date,
        earliest_resource_id,
    )


def can_assign_resource(resource, task, start_date, end_date, assignment=None):
    resource = Resource.objects.get(id=resource)
    task = Task.objects.get(id=task)

    # Check if the resource has the required skills
    if not task.skills_required.filter(id__in=resource.skills.all()).exists():
        return False

    # Check if the resource is available during the specified start and end dates
    if resource.availability_start_date and resource.availability_start_date > end_date:
        return False
    if resource.availability_end_date and resource.availability_end_date < start_date:
        return False

    # Check if the resource is already assigned during the specified start and end dates
    existing_assignments = Assignments.objects.filter(
        resource=resource,
        start_date__lte=end_date,
        end_date__gte=start_date,
        status="ASSIGNED",
    )
    if assignment:
        existing_assignments = existing_assignments.exclude(pk=assignment)
    if existing_assignments.exists():
        return False

    return True
