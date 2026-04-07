import pytest


def test_parse_svg_path_moveto_lineto():
    """Should parse simple M/L path commands into points."""
    from scripts.helpers import parse_svg_to_contours

    # Simple square: M 0,0 L 100,0 L 100,100 L 0,100 Z
    svg_content = '''<svg><path d="M 0,0 L 100,0 L 100,100 L 0,100 Z"/></svg>'''
    contours = parse_svg_to_contours(svg_content)
    assert len(contours) == 1
    assert len(contours[0]) >= 4  # at least 4 points for a square


def test_parse_svg_path_curves():
    """Should parse cubic Bezier (C) commands."""
    from scripts.helpers import parse_svg_to_contours

    svg_content = '''<svg><path d="M 0,0 C 10,20 30,40 50,50 Z"/></svg>'''
    contours = parse_svg_to_contours(svg_content)
    assert len(contours) == 1
    assert len(contours[0]) > 0


def test_parse_svg_multiple_contours():
    """SVG with multiple subpaths should produce multiple contours."""
    from scripts.helpers import parse_svg_to_contours

    svg_content = '''<svg>
        <path d="M 0,0 L 10,0 L 10,10 Z M 20,20 L 30,20 L 30,30 Z"/>
    </svg>'''
    contours = parse_svg_to_contours(svg_content)
    assert len(contours) == 2
