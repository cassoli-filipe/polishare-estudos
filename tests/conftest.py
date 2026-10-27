from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture():
    def ler(nome: str) -> str:
        return (FIXTURES / f"{nome}.html").read_text(encoding="utf-8")

    return ler
