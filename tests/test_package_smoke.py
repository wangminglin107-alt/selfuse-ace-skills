def test_package_exposes_version():
    import research_skills_os

    assert research_skills_os.__version__ == "0.1.0"
