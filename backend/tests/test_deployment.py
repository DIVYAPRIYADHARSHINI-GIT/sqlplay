from pathlib import Path
import tomllib

def test_vercel_and_local_dependencies_match():
    root = Path(__file__).parents[1]
    metadata = tomllib.loads((root / 'pyproject.toml').read_text())
    requirements = set((root / 'requirements.txt').read_text().splitlines())
    assert set(metadata['project']['dependencies']) == requirements
    assert 'fastapi==0.115.12' in requirements
