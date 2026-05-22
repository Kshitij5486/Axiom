content = open("tests/unit/test_nlp.py", "r", encoding="utf-8").read()

# The dag_updater imports from db directly
# Need to mock at the dag_updater module level
content = content.replace(
    '"db.get_current_causal_effects"',
    '"dag_updater.get_current_causal_effects"'
)
content = content.replace(
    '"db.update_causal_graph_effects"',
    '"dag_updater.update_causal_graph_effects"'
)

# Also add the functions to dag_updater namespace in tests
# by importing them at top of each test class
old = "    def _make_effects(self):"
new = """    def setup_method(self):
        import dag_updater
        import db as nlp_db
        dag_updater.get_current_causal_effects = nlp_db.get_current_causal_effects
        dag_updater.update_causal_graph_effects = nlp_db.update_causal_graph_effects

    def _make_effects(self):"""

content = content.replace(old, new)

open("tests/unit/test_nlp.py", "w", encoding="utf-8").write(content)
print("Fixed")