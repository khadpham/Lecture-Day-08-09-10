import unittest
from unittest.mock import patch

from rag_answer import rag_answer


def _fake_retrieve_dense(query: str, top_k: int = 10):
    if "SLA" in query.upper() and "P1" in query.upper():
        return [
            {
                "text": "Theo tài liệu SLA P1 2026, ticket mức P1 phải được phản hồi trong 15 phút.",
                "metadata": {
                    "source": "sla_p1_2026.txt",
                    "section": "SLA",
                    "effective_date": "2026-01-01",
                },
                "score": 0.92,
            }
        ]
    return []


def _fake_call_llm(prompt: str) -> str:
    if "ERR-403-AUTH" in prompt:
        return "Không đủ dữ liệu trong ngữ cảnh để trả lời."
    return "SLA ticket P1 là 15 phút [1]."


class TestSprint2Acceptance(unittest.TestCase):
    @patch("rag_answer.retrieve_dense", side_effect=_fake_retrieve_dense)
    @patch("rag_answer.call_llm", side_effect=_fake_call_llm)
    def test_sla_answer_has_citation_and_non_empty_sources(self, _mock_llm, _mock_retrieve):
        result = rag_answer("SLA ticket P1?", retrieval_mode="dense", verbose=False)

        self.assertIn("answer", result)
        self.assertIn("[1]", result["answer"])
        self.assertIn("sources", result)
        self.assertTrue(result["sources"], "sources không được rỗng cho câu có context")

    @patch("rag_answer.retrieve_dense", side_effect=_fake_retrieve_dense)
    @patch("rag_answer.call_llm", side_effect=_fake_call_llm)
    def test_unknown_query_abstains(self, _mock_llm, _mock_retrieve):
        result = rag_answer("ERR-403-AUTH", retrieval_mode="dense", verbose=False)

        self.assertIn("answer", result)
        self.assertIn("không đủ dữ liệu", result["answer"].lower())


if __name__ == "__main__":
    unittest.main()
