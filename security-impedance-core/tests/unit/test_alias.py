from impedance.alias import alias_path, is_alias

def test_roundtrip():
    p = "/var/log/app.log"
    tok = alias_path(p)
    assert is_alias(tok) and tok.startswith("FILE_")

def test_deterministic():
    """Test that aliasing is deterministic"""
    p1 = "/home/user/secret.txt"
    p2 = "/home/user/secret.txt"
    assert alias_path(p1) == alias_path(p2)

def test_different_paths_different_aliases():
    """Test that different paths get different aliases"""
    p1 = "/path/one.txt"
    p2 = "/path/two.txt"
    assert alias_path(p1) != alias_path(p2)

def test_alias_format():
    """Test alias format matches expected pattern"""
    p = "/test/path.txt"
    alias = alias_path(p)
    assert alias.startswith("FILE_")
    assert len(alias) == 13  # "FILE_" + 8 hex chars
    assert is_alias(alias)