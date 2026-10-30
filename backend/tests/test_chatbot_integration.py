"""
AI Agronomist Chatbot Integration Tests.
Executes against an isolated ephemeral database and test client shared across the test runner.
"""
import unittest
import warnings

# Suppress harmless testclient deprecation warning and resource warnings during test runs
warnings.filterwarnings("ignore", message=r".*httpx.*", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=ResourceWarning)

from tests import test_api_regression as base


def setUpModule():
    base.acquire()


def tearDownModule():
    base.release()


class TestChatbotIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = base.client
        cls.headers1 = base.register("chat_alice")
        cls.headers2 = base.register("chat_bob")

    def test_01_send_message_creates_new_conversation(self):
        """Posting a message without conversation_id starts a new conversation."""
        prompt = "What is causing yellow spots on my tomato leaves?"
        res = self.client.post(
            "/api/chatbot/message",
            headers=self.headers1,
            json={"message": prompt}
        )
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertIn("id", data)
        self.assertGreater(data["id"], 0)
        self.assertIn("tomato", data["title"].lower())

        messages = data.get("messages", [])
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[0]["content"], prompt)
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertIn("spot", messages[1]["content"].lower())

    def test_02_send_message_in_existing_conversation(self):
        """Posting a message with an existing conversation_id appends to the conversation."""
        # Create initial conversation
        r1 = self.client.post(
            "/api/chatbot/message",
            headers=self.headers1,
            json={"message": "Can you give me irrigation advice for potato?"}
        )
        self.assertEqual(r1.status_code, 200)
        conv_id = r1.json()["id"]

        # Follow-up message
        r2 = self.client.post(
            "/api/chatbot/message",
            headers=self.headers1,
            json={"conversation_id": conv_id, "message": "What about soil moisture requirements?"}
        )
        self.assertEqual(r2.status_code, 200)
        data2 = r2.json()
        self.assertEqual(data2["id"], conv_id)
        messages = data2.get("messages", [])
        self.assertEqual(len(messages), 4)
        self.assertEqual(messages[2]["content"], "What about soil moisture requirements?")
        self.assertEqual(messages[3]["role"], "assistant")

    def test_03_list_conversations_returns_user_conversations(self):
        """Listing conversations returns user-scoped conversations ordered newest first."""
        res = self.client.get("/api/chatbot/conversations", headers=self.headers1)
        self.assertEqual(res.status_code, 200)
        convs = res.json()
        self.assertIsInstance(convs, list)
        self.assertGreaterEqual(len(convs), 2)
        for c in convs:
            self.assertIn("id", c)
            self.assertIn("title", c)
            self.assertIn("created_at", c)
            self.assertIn("message_count", c)

    def test_04_get_conversation_with_messages(self):
        """Retrieving a specific conversation includes its full message history."""
        list_res = self.client.get("/api/chatbot/conversations", headers=self.headers1)
        target_id = list_res.json()[0]["id"]

        res = self.client.get(f"/api/chatbot/conversations/{target_id}", headers=self.headers1)
        self.assertEqual(res.status_code, 200)
        conv = res.json()
        self.assertEqual(conv["id"], target_id)
        self.assertTrue(len(conv["messages"]) >= 2)

    def test_05_multi_tenant_isolation(self):
        """User 2 cannot read or append to User 1's conversations."""
        # Get conv id created by user 1
        list_res = self.client.get("/api/chatbot/conversations", headers=self.headers1)
        target_id_1 = list_res.json()[0]["id"]

        # User 2 attempts to fetch it
        res_get = self.client.get(f"/api/chatbot/conversations/{target_id_1}", headers=self.headers2)
        self.assertEqual(res_get.status_code, 404)

        # User 2 attempts to post to it
        res_post = self.client.post(
            "/api/chatbot/message",
            headers=self.headers2,
            json={"conversation_id": target_id_1, "message": "Malicious attempt"}
        )
        self.assertEqual(res_post.status_code, 404)

    def test_06_delete_conversation(self):
        """Deleting a conversation removes it and cascades message cleanup."""
        # Create dedicated conv to delete
        res = self.client.post(
            "/api/chatbot/message",
            headers=self.headers1,
            json={"message": "Temporary conversation to delete"}
        )
        conv_id = res.json()["id"]

        del_res = self.client.delete(f"/api/chatbot/conversations/{conv_id}", headers=self.headers1)
        self.assertEqual(del_res.status_code, 200)

        # Verify it no longer exists
        check_res = self.client.get(f"/api/chatbot/conversations/{conv_id}", headers=self.headers1)
        self.assertEqual(check_res.status_code, 404)

    def test_07_unauthenticated_requests_rejected(self):
        """Accessing chatbot routes without token returns HTTP 401 or 403."""
        r1 = self.client.get("/api/chatbot/conversations")
        self.assertIn(r1.status_code, (401, 403))

        r2 = self.client.post("/api/chatbot/message", json={"message": "Hello"})
        self.assertIn(r2.status_code, (401, 403))


if __name__ == "__main__":
    unittest.main()
