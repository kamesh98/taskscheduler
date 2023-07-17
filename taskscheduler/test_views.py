from datetime import date, timedelta

import freezegun
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from taskscheduler.models import Assignments, Project, Resource, Skill, Task


@freezegun.freeze_time("2023-07-17")
class ProjectAPITestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()

    def test_create_project(self):
        url = reverse("project-list")
        data = {
            "name": "Project 1",
            "start_date": "2023-07-01",
            "end_date": "2023-07-10",
            "completed": False,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        project_id = response.json()["id"]
        self.assertIsNotNone(project_id)

    def test_update_project(self):
        url = reverse("project-list")
        data = {
            "name": "Project 1",
            "start_date": "2023-07-01",
            "end_date": "2023-07-10",
            "completed": False,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        project_id = response.json()["id"]
        self.assertIsNotNone(project_id)

        update_url = reverse("project-detail", kwargs={"pk": project_id})
        updated_data = {
            "name": "Updated Project",
            "start_date": "2023-07-05",
            "end_date": "2023-07-15",
            "completed": True,
        }
        response = self.client.put(update_url, updated_data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_delete_project(self):
        url = reverse("project-list")
        data = {
            "name": "Project 1",
            "start_date": "2023-07-01",
            "end_date": "2023-07-10",
            "completed": False,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        project_id = response.json()["id"]
        self.assertIsNotNone(project_id)

        delete_url = reverse("project-detail", kwargs={"pk": project_id})
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, 204)


@freezegun.freeze_time("2023-07-17")
class TaskAPITestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.project = Project.objects.create(
            name="Your Project",
            created_date=date.today(),
            is_deleted=False,
            completed=False,
        )
        self.skill = Skill.objects.create(name="backend")
        self.resource = Resource.objects.create(
            name="Resource 1", availability_start_date=date.today()
        )
        self.resource.skills.set([self.skill])

    def test_create_task(self):
        url = f"/api/tasks/"
        data = {
            "project": self.project.id,
            "name": "Test Task",
            "start_date": "2023-07-01",
            "end_date": "2023-07-05",
            "completed": False,
            "skills_required": [self.skill.id],
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(Task.objects.first().name, "Test Task")

    def test_update_task(self):
        task = Task.objects.create(
            project=self.project,
            name="Old Task",
            estimation=3,
            created_date=date.today(),
            is_deleted=False,
            completed=False,
        )
        url = f"/api/tasks/{task.id}/"
        data = {
            "name": "New Task",
            "project": self.project.id,
            "skills_required": [self.skill.id],
        }

        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Task.objects.get(id=task.id).name, "New Task")

    def test_update_task_failure(self):
        task = Task.objects.create(
            project=self.project,
            name="Old Task",
            estimation=3,
            created_date=date.today(),
            is_deleted=False,
            completed=False,
        )
        url = f"/api/tasks/{task.id}/"
        data = {
            "name": "New Task",
            "skills_required": [self.skill.id],
        }

        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_retrieve_task_with_assignments(self):
        task = Task.objects.create(
            project=self.project,
            name="Test Task",
            estimation=3,
            created_date=date.today(),
            is_deleted=False,
            completed=False,
        )
        Assignments.objects.create(
            status="ASSIGNED",
            resource=self.resource,
            task=task,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )
        url = f"/api/tasks/{task.id}/?show_assignments=true"

        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], task.id)
        self.assertIn("assignment", response.data)
        self.assertIn("assigned_resource", response.data)

    def test_update_completed_task(self):
        task = Task.objects.create(
            project=self.project,
            name="Test Task",
            estimation=3,
            created_date=date.today(),
            is_deleted=False,
            completed=False,
        )
        Assignments.objects.create(
            status="ASSIGNED",
            resource=self.resource,
            task=task,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )

        url = reverse("task-detail", kwargs={"pk": task.id})
        data = {"completed": True}

        response = self.client.patch(url, data, format="json")
        assignment = Assignments.objects.get(task=task)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Task.objects.get(id=task.id).completed, True)
        self.assertEqual(assignment.status, "COMPLETED")

    def test_update_non_completed_task(self):
        task = Task.objects.create(
            project=self.project,
            name="Test Task",
            estimation=3,
            created_date=date.today(),
            is_deleted=False,
            completed=True,
        )
        Assignments.objects.create(
            status="COMPLETED",
            resource=self.resource,
            task=task,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )
        url = reverse("task-detail", kwargs={"pk": task.id})
        data = {"completed": False}

        response = self.client.patch(url, data, format="json")
        assignment = Assignments.objects.get(task=task)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Task.objects.get(id=task.id).completed, True)
        self.assertEqual(assignment.status, "COMPLETED")


@freezegun.freeze_time("2023-07-17")
class AssignmentsViewSetTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.project = Project.objects.create(
            name="Your Project",
            created_date=date.today() - timedelta(days=10),
            is_deleted=False,
            completed=False,
        )
        self.skill = Skill.objects.create(name="backend")
        self.resource = Resource.objects.create(
            name="Resource 1", availability_start_date=date.today() - timedelta(days=15)
        )
        self.resource.skills.set([self.skill])
        self.task = Task.objects.create(
            project=self.project,
            name="Test Task",
            estimation=3,
            created_date=date.today(),
            is_deleted=False,
            completed=False,
        )
        self.task.skills_required.set([self.skill])

    def test_create_assignment(self):
        # Cannot create assignments
        assignment_data = {
            "task": 1,
            "resource": 1,
            "start_date": "2023-07-17",
            "end_date": "2023-07-10",
            "status": "ASSIGNED",
        }
        response = self.client.post("/api/assignment/", assignment_data, format="json")
        self.assertEqual(response.status_code, 405)

    def test_update_assignment_status(self):
        # Create a new assignment
        assignment = Assignments.objects.create(
            status="ASSIGNED",
            resource=self.resource,
            task=self.task,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )
        # Update the status of the assignment from 'ASSIGNED' to 'COMPLETED'
        updated_assignment_data = {
            "status": "COMPLETED",
            "start_date": "2023-07-05",
            "end_date": "2023-07-15",
        }

        response = self.client.patch(
            f"/api/assignment/{assignment.id}/", updated_assignment_data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "COMPLETED")

    def test_update_assignment_dates(self):
        # Create a new assignment
        assignment = Assignments.objects.create(
            status="ASSIGNED",
            resource=self.resource,
            task=self.task,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )

        # Update the start_date and end_date of the assignment
        updated_assignment_data = {"start_date": "2023-07-05", "end_date": "2023-07-15"}
        response = self.client.patch(
            f"/api/assignment/{assignment.id}/", updated_assignment_data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["start_date"], "2023-07-05")
        self.assertEqual(response.data["end_date"], "2023-07-15")

    def test_delete_assignment(self):
        # Create a new assignment
        assignment = Assignments.objects.create(
            status="ASSIGNED",
            resource=self.resource,
            task=self.task,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )

        # Delete the assignment
        response = self.client.delete(f"/api/assignment/{assignment.id}/")
        self.assertEqual(response.status_code, 204)

    def test_get_assignment(self):
        # Cannot create assignments
        assignment = Assignments.objects.create(
            status="ASSIGNED",
            resource=self.resource,
            task=self.task,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )

        # Retrieve the assignment
        response = self.client.get(f"/api/assignment/{assignment.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], assignment.id)
