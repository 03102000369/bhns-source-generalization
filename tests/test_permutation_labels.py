from bhns.experiments.source_permutation import permute_source_labels


def test_fake_labels_are_constant_within_each_source(observations):
    original = observations.compact_object_class.copy()
    labels, mapping = permute_source_labels(observations, seed=42)
    assert labels.groupby(observations.source_name).nunique().eq(1).all()
    assert sum(mapping.values()) == 6
    assert observations.compact_object_class.equals(original)


def test_permutations_differ_and_reproduce(observations):
    _, first = permute_source_labels(observations, seed=42)
    _, second = permute_source_labels(observations, seed=43)
    _, repeated = permute_source_labels(observations, seed=42)
    assert first != second
    assert first == repeated


def test_source_mapping_independent_of_observation_order(observations):
    _, first = permute_source_labels(observations, seed=42)
    _, reordered = permute_source_labels(observations.iloc[::-1], seed=42)
    assert first == reordered
