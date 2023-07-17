import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "taskscheduler.settings")
import django

django.setup()

from datetime import date

import freezegun
import requests
from django.urls import reverse

from taskscheduler.models import Project, Resource, Skill, Task


@freezegun.freeze_time("2023-07-17")
def test_working_example():
    # Create skills
    backend_skill = Skill.objects.create(name="backend")
    frontend_skill = Skill.objects.create(name="frontend")
    deployment_skill = Skill.objects.create(name="deployment")
    design_skill = Skill.objects.create(name="design")

    # Create a project
    project = Project.objects.create(
        name="Your Project",
        created_date=date.today(),
        is_deleted=False,
        completed=False,
    )

    # Create tasks
    task1 = Task.objects.create(
        project=project,
        name="Task 1",
        estimation=3,
        created_date=date.today(),
        is_deleted=False,
        completed=False,
    )
    task1.skills_required.set([backend_skill])

    task2 = Task.objects.create(
        project=project,
        name="Task 2",
        estimation=3,
        created_date=date.today(),
        is_deleted=False,
        completed=False,
    )
    task2.skills_required.set([frontend_skill])

    task3 = Task.objects.create(
        project=project,
        name="Task 3",
        estimation=3,
        created_date=date.today(),
        is_deleted=False,
        completed=False,
    )
    task3.skills_required.set([backend_skill, deployment_skill])

    task4 = Task.objects.create(
        project=project,
        name="Task 4",
        estimation=2,
        created_date=date.today(),
        is_deleted=False,
        completed=False,
    )
    task4.skills_required.set([deployment_skill])

    task5 = Task.objects.create(
        project=project,
        name="Task 5",
        estimation=1,
        created_date=date.today(),
        is_deleted=False,
        completed=False,
    )
    task5.skills_required.set([design_skill])

    task6 = Task.objects.create(
        project=project,
        name="Task 6",
        estimation=5,
        start_date=date(2023, 8, 7),
        end_date=date(2023, 8, 14),
        created_date=date.today(),
        is_deleted=False,
        completed=False,
    )
    task6.skills_required.set([backend_skill])

    task7 = Task.objects.create(
        project=project,
        name="Task 7",
        estimation=2,
        start_date=date(2023, 7, 26),
        end_date=date(2023, 8, 3),
        created_date=date.today(),
        is_deleted=False,
        completed=False,
    )
    task7.skills_required.set([backend_skill])

    # Create resources
    resource1 = Resource.objects.create(
        name="Resource 1", availability_start_date=date.today()
    )
    resource1.skills.set([backend_skill, deployment_skill])

    resource2 = Resource.objects.create(
        name="Resource 2", availability_start_date=date.today()
    )
    resource2.skills.set([frontend_skill])

    resource3 = Resource.objects.create(
        name="Resource 3", availability_start_date=date.today()
    )
    resource3.skills.set([design_skill])

    resource4 = Resource.objects.create(
        name="Resource 4", availability_start_date=date.today()
    )
    resource4.skills.set([deployment_skill])

    plan_url = reverse("assign")
    data = {"project_id": project.id}
    response = requests.post(f"http://127.0.0.1:8000{plan_url}", data=data)

    expected_response = [
        {
            "task_id": task7.id,
            "resource_id": resource1.id,
            "start_date": "2023-07-26",
            "end_date": "2023-07-28",
        },
        {
            "task_id": task6.id,
            "resource_id": resource1.id,
            "start_date": "2023-08-07",
            "end_date": "2023-08-12",
        },
        {
            "task_id": task1.id,
            "resource_id": resource1.id,
            "start_date": "2023-07-18",
            "end_date": "2023-07-21",
        },
        {
            "task_id": task2.id,
            "resource_id": resource2.id,
            "start_date": "2023-07-18",
            "end_date": "2023-07-21",
        },
        {
            "task_id": task3.id,
            "resource_id": resource1.id,
            "start_date": "2023-07-22",
            "end_date": "2023-07-25",
        },
        {
            "task_id": task4.id,
            "resource_id": resource4.id,
            "start_date": "2023-07-18",
            "end_date": "2023-07-20",
        },
        {
            "task_id": task5.id,
            "resource_id": resource3.id,
            "start_date": "2023-07-18",
            "end_date": "2023-07-19",
        },
    ]

    api_output = response.json()
    sorted_api_output = sorted(api_output, key=lambda x: x["task_id"])
    sorted_expected_response = sorted(expected_response, key=lambda x: x["task_id"])
    assert sorted_api_output == sorted_expected_response


if __name__ == "__main__":
    test_working_example()
