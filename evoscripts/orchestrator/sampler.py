"""Data sampling utilities for JSONL files."""

import json
import random
from pathlib import Path

from evoscripts.orchestrator.state import Sample


class Sampler:
    """Handles random sampling from JSONL data files."""

    def __init__(self, data_path: str, seed: int | None = None):
        """Initialize the sampler.

        Args:
            data_path: Path to the JSONL file.
            seed: Random seed for reproducibility.
        """
        self.data_path = Path(data_path)
        self._samples: list[Sample] | None = None
        self._rng = random.Random(seed)

        if not self.data_path.exists():
            raise FileNotFoundError(f"Data file not found: {data_path}")

    def _load_all(self) -> list[Sample]:
        """Load all samples from the JSONL file."""
        if self._samples is not None:
            return self._samples

        samples = []
        with open(self.data_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    samples.append(Sample(index=i, data=data, raw_line=line))
                except json.JSONDecodeError as e:
                    # Skip malformed lines but log them
                    print(f"Warning: Skipping malformed line {i}: {e}")

        self._samples = samples
        return samples

    @property
    def total_count(self) -> int:
        """Return total number of valid samples."""
        return len(self._load_all())

    def sample(self, n: int) -> list[Sample]:
        """Randomly sample n items from the data.

        Args:
            n: Number of items to sample.

        Returns:
            List of sampled items.
        """
        all_samples = self._load_all()
        n = min(n, len(all_samples))
        return self._rng.sample(all_samples, n)

    def sample_indices(self, indices: list[int]) -> list[Sample]:
        """Get samples by their indices.

        Args:
            indices: List of sample indices.

        Returns:
            List of samples at the specified indices.
        """
        all_samples = self._load_all()
        return [all_samples[i] for i in indices if 0 <= i < len(all_samples)]

    def get_sample_data(self, samples: list[Sample]) -> list[dict]:
        """Extract just the data dictionaries from samples.

        Args:
            samples: List of Sample objects.

        Returns:
            List of data dictionaries.
        """
        return [s.data for s in samples]
