from django.test import TestCase


class HealthCheckTests(TestCase):
    def test_health_check_confirms_database_connection(self):
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_check_rejects_non_get_requests(self):
        response = self.client.post("/health/")

        self.assertEqual(response.status_code, 405)
