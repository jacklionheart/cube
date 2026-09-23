import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from render import card_gallery, render_page, tabbed_panels


class AuthoringTests(unittest.TestCase):
    def test_prose_and_generated_values_compose(self):
        page = render_page('Example', '# A post\n\nMy **argument** uses {{count}} decks.\n\n{{gallery}}',
                           {'count': '13', 'gallery': '<div>cards</div>'}, hover=False)
        self.assertIn('<h1>A post</h1>', page)
        self.assertIn('My <b>argument</b> uses 13 decks.', page)
        self.assertIn('<div>cards</div>', page)
        self.assertIn('name=\'viewport\'', page)

    def test_missing_component_fails_instead_of_publishing_a_placeholder(self):
        with self.assertRaises(KeyError):
            render_page('Example', '{{missing}}', {})

    def test_gallery_links_escape_names_and_preserve_order(self):
        cards = ['Zed', 'A "quoted" card']
        page = card_gallery(cards, {c: 'https://example/card.png' for c in cards},
                            captions={c: '13 decks' for c in cards})
        self.assertLess(page.index("alt='Zed'"), page.index('alt=\'A &quot;quoted&quot; card\''))
        self.assertEqual(page.count('data-img='), 2)
        self.assertEqual(page.count('13 decks'), 2)

    def test_tab_controls_reference_their_own_panels(self):
        page = tabbed_panels('blue', [('First', '<p>A</p>'), ('Second', '<p>B</p>')], label='Colors')
        self.assertIn("aria-controls='blue-pane-0'", page)
        self.assertIn("aria-selected='true' tabindex='0'", page)
        self.assertIn("aria-labelledby='blue-tab-1' tabindex='0' hidden", page)


if __name__ == '__main__':
    unittest.main()
