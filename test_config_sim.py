import config_sim as cs
import pytest
import test_boards

@pytest.fixture
def example_seq():
    return [0,1,2,3,4,5,6]


def test_tiny_sample_empty():
    assert len(cs.tiny_sample([],5)) == 0

def test_tiny_sample_basic(example_seq):
    for _ in range(100):
        assert all(num in example_seq for num in cs.tiny_sample(example_seq,3))

def test_tiny_sample_same_length(example_seq):
    assert(set(example_seq) == set(cs.tiny_sample(example_seq,len(example_seq))))

def test_tiny_sample_zero(example_seq):
    assert len(cs.tiny_sample(example_seq,0)) == 0

def mock_tiny_sample(seq,k):
    if len(seq) == 0:
        return []
    n = len(seq)
    if k == 0:
        return []
    if k == n:
        return list(seq)
    return seq[:k]

# def test_


