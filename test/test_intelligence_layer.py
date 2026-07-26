#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
import unittest
from rag.intelligence.events.schemas import EnterpriseEvent, EventTypes
from rag.intelligence.events.event_bus import EventBus
from rag.intelligence.security.anonymizer import PIIAnonymizer
from rag.intelligence.extractors.entity_extractor import EntityExtractorPlugin
from rag.intelligence.extractors.decision_extractor import DecisionExtractorPlugin
from rag.intelligence.extractors.topic_extractor import TopicExtractorPlugin
from rag.intelligence.extractors.expertise_extractor import ExpertiseExtractorPlugin


class TestEnterpriseIntelligenceLayer(unittest.TestCase):

    def test_pii_anonymizer(self):
        sample_text = "Contact John at john.smith@example.com or call +1-555-0199."
        clean_text, meta = PIIAnonymizer.sanitize(sample_text)
        self.assertTrue(meta["pii_detected"])
        self.assertNotIn("john.smith@example.com", clean_text)
        self.assertIn("[ANONYMIZED_EMAIL]", clean_text)
        self.assertIn("[ANONYMIZED_PHONE]", clean_text)

    def test_event_bus(self):
        event = EnterpriseEvent(
            event_type=EventTypes.CONVERSATION_FINISHED,
            tenant_id="tenant_test_123",
            payload={"chat_id": "chat_001"},
            user_id="user_test_001"
        )
        self.assertEqual(event.event_type, "ConversationFinished")

        received = []
        bus = EventBus()
        bus.register_subscriber(EventTypes.CONVERSATION_FINISHED, lambda e: received.append(e))
        bus.dispatch_local(event)
        self.assertEqual(len(received), 1)

    def test_extractors_structure(self):
        e_plugin = EntityExtractorPlugin()
        d_plugin = DecisionExtractorPlugin()
        t_plugin = TopicExtractorPlugin()
        exp_plugin = ExpertiseExtractorPlugin()

        self.assertEqual(e_plugin.plugin_name, "entity_and_relationship_extractor")
        self.assertEqual(d_plugin.plugin_name, "decision_and_action_item_extractor")
        self.assertEqual(t_plugin.plugin_name, "topic_and_tech_stack_extractor")
        self.assertEqual(exp_plugin.plugin_name, "expertise_signal_extractor")

        sample_transcript = "We decided to migrate database to Neo4j. Task assigned to Alice."
        res_e = e_plugin.extract(sample_transcript, {})
        res_d = d_plugin.extract(sample_transcript, {})
        res_t = t_plugin.extract(sample_transcript, {})
        res_exp = exp_plugin.extract(sample_transcript, {})

        self.assertIn("entities", res_e)
        self.assertIn("decisions", res_d)
        self.assertIn("topics", res_t)
        self.assertIn("expertise_signals", res_exp)

    def test_onboarding_payload_structure(self):
        sample_payload = {
            "purpose": "Knowledge Base & RAG Management",
            "intended_use": "Building internal AI assistants for employees",
            "company_name": "Tech Corp",
            "company_size": "51-200",
            "industry": "Software / Technology",
            "role": "Lead Architect",
            "platform_goals": "Reduce search time and automate document Q&A"
        }
        self.assertIn("purpose", sample_payload)
        self.assertIn("company_name", sample_payload)
        self.assertEqual(sample_payload["company_size"], "51-200")


if __name__ == "__main__":
    unittest.main()
