from datetime import datetime, timedelta, timezone
import unittest


from app.domain.chat_retention import ChatRetentionPolicy, MAX_CHAT_RETENTION_DAYS


class ChatRetentionPolicyTest(unittest.TestCase):
    def test_chat_retention_policy_caps_storage_at_ten_days(self) -> None:
        with self.assertRaises(ValueError):
            ChatRetentionPolicy(max_age_days=MAX_CHAT_RETENTION_DAYS + 1)

    def test_chat_retention_policy_calculates_cutoff_and_expiry(self) -> None:
        now = datetime(2026, 4, 22, 12, 0, tzinfo=timezone.utc)
        policy = ChatRetentionPolicy(max_age_days=10)

        self.assertEqual(policy.cutoff(now), datetime(2026, 4, 12, 12, 0, tzinfo=timezone.utc))
        self.assertTrue(policy.is_expired(now - timedelta(days=10, seconds=1), now))
        self.assertFalse(policy.is_expired(now - timedelta(days=10), now))


if __name__ == "__main__":
    unittest.main()
