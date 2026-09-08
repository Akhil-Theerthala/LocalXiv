"""Focused tests for Pandoc's duplicated anchors on nested table grids."""
import unittest
from xml.etree import ElementTree as ET

from papers.document import XHTML, _normalize_structure, local


def table(identifier, caption, value):
    item = ET.Element(f"{{{XHTML}}}table", {"id": identifier})
    ET.SubElement(item, f"{{{XHTML}}}caption").text = caption
    row = ET.SubElement(item, f"{{{XHTML}}}tr")
    ET.SubElement(row, f"{{{XHTML}}}td").text = value
    return item


class NestedTableAnchorTests(unittest.TestCase):
    def test_proven_sibling_grids_keep_one_group_anchor_and_caption(self):
        root = ET.Element(f"{{{XHTML}}}body")
        for value in ("A", "B", "C"):
            root.append(table("tab:group", "Shared caption", value))
        warnings = []
        normalized = _normalize_structure(root, warnings=warnings, table_groups={"tab:group": 3})
        groups = normalized.findall("./{*}figure")
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].get("id"), "tab:group")
        self.assertEqual(len(groups[0].findall("./{*}table")), 3)
        self.assertEqual("Shared caption", "".join(groups[0].find("./{*}figcaption").itertext()))
        self.assertEqual([t.get("id") for t in groups[0].findall("./{*}table")], [None, None, None])
        self.assertEqual(["A", "B", "C"], ["".join(t.itertext()).replace("Shared caption", "").strip() for t in groups[0].findall("./{*}table")])
        self.assertTrue(any("shared caption" in warning.lower() for warning in warnings))

    def test_nested_grids_require_matching_caption_and_source_shape(self):
        import copy
        root = ET.Element(f"{{{XHTML}}}body")
        outer = table('tab:group', 'Shared caption', '')
        root.append(outer)
        cell = outer.find('.//{*}td')
        for value in ('0.00125', '-2.50', '3.14'):
            cell.append(table('tab:group', 'Shared caption', value))
        for evidence in ({}, {'tab:group': 3}):
            with self.assertRaises(ValueError):
                _normalize_structure(copy.deepcopy(root), nested_table_groups=evidence)
        broken = copy.deepcopy(root)
        broken.findall('.//{*}caption')[-1].text = 'Different caption'
        with self.assertRaises(ValueError):
            _normalize_structure(broken, nested_table_groups={'tab:group': 4})
        _normalize_structure(root, nested_table_groups={'tab:group': 4})
        self.assertEqual(len(root.findall('.//{*}table')), 4)
        self.assertEqual(len(root.findall('.//{*}caption')), 1)
        self.assertEqual([e.get('id') for e in root.iter() if e.get('id')], ['tab:group'])
        self.assertEqual([e.text for e in root.findall('.//{*}td')][1:], ['0.00125', '-2.50', '3.14'])
        _normalize_structure(root, nested_table_groups={'tab:group': 4})

    def test_unproven_duplicate_anchor_is_rejected(self):
        root = ET.Element(f"{{{XHTML}}}body")
        root.append(table("tab:duplicate", "One", "A"))
        root.append(table("tab:duplicate", "Two", "B"))
        with self.assertRaises(ValueError):
            _normalize_structure(root, table_groups={})


if __name__ == "__main__":
    unittest.main()
