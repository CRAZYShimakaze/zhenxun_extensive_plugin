import unittest

from utils import normalize_name, resolve_name, version_key


class ResolveNameTests(unittest.TestCase):
    def test_matches_punctuation_variants(self):
        self.assertEqual(resolve_name("零号安比", ["零号·安比"]), "零号·安比")

    def test_resolves_alias_to_available_asset_name(self):
        aliases = {
            "柳": ["月城柳"],
            "奥菲丝&「鬼火」": ["奥菲丝", "鬼火"],
        }
        self.assertEqual(resolve_name("柳", ["月城柳"], aliases), "月城柳")
        self.assertEqual(resolve_name("鬼火", ["奥菲丝"], aliases), "奥菲丝")

    def test_rejects_unknown_name(self):
        self.assertIsNone(resolve_name("不存在", ["安比"]))


class UtilityTests(unittest.TestCase):
    def test_normalize_name(self):
        self.assertEqual(normalize_name("「11号」"), "11号")

    def test_version_key(self):
        self.assertGreater(version_key("1.10"), version_key("1.9"))


if __name__ == "__main__":
    unittest.main()
