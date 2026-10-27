import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from exams.models import Paper, Question


def normalize_text(value: str) -> str:
    value = (value or "").lower()
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def _combined_similarity(query: str, documents: list[str]) -> list[float]:
    if not query or not documents:
        return []
    corpus = [query, *documents]
    word = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    char = TfidfVectorizer(
        analyzer="char_wb", ngram_range=(3, 5), min_df=1, sublinear_tf=True
    )
    word_matrix = word.fit_transform(corpus)
    char_matrix = char.fit_transform(corpus)
    word_scores = cosine_similarity(word_matrix[0:1], word_matrix[1:]).ravel()
    char_scores = cosine_similarity(char_matrix[0:1], char_matrix[1:]).ravel()
    return [float((0.65 * w) + (0.35 * c)) for w, c in zip(word_scores, char_scores)]


def find_candidate_matches(text: str, limit: int = 10) -> list[dict]:
    query = normalize_text(text)
    questions = list(
        Question.objects.select_related("paper__exam").filter(
            paper__status=Paper.Status.READY
        )
    )
    rows = []
    if questions:
        scores = _combined_similarity(
            query, [normalize_text(q.text) for q in questions]
        )
        rows.extend(
            {"paper": q.paper, "question": q, "score": score}
            for q, score in zip(questions, scores)
        )

    papers_without_questions = list(
        Paper.objects.select_related("exam")
        .filter(status=Paper.Status.READY, questions__isnull=True)
        .exclude(extracted_text="")
        .distinct()
    )
    if papers_without_questions:
        scores = _combined_similarity(
            query, [normalize_text(p.extracted_text) for p in papers_without_questions]
        )
        rows.extend(
            {"paper": p, "question": None, "score": score}
            for p, score in zip(papers_without_questions, scores)
        )

    rows.sort(key=lambda row: row["score"], reverse=True)
    return rows[:limit]


def excerpt(text: str, max_length: int = 500) -> str:
    cleaned = " ".join((text or "").split())
    return cleaned[:max_length] + ("…" if len(cleaned) > max_length else "")
