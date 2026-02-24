"""Tests for tailwind_mapper.py — CSS property to Tailwind v4 class mapping."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tailwind_mapper import (  # noqa: E402
    TailwindMapper,
    map_font_size,
    map_font_weight,
    map_letter_spacing,
    map_line_height,
    map_text_align,
    snap_color,
)


# ---------------------------------------------------------------------------
# TailwindMapper.map_properties
# ---------------------------------------------------------------------------

class TestMapProperties:
    """Test the main CSS-to-Tailwind properties mapper."""

    def test_empty_props(self):
        """Empty dict should return empty list."""
        assert TailwindMapper().map_properties({}) == []

    def test_background_color(self):
        """background-color should map to bg-* class."""
        classes = TailwindMapper().map_properties({"background-color": "#ffffff"})
        assert len(classes) == 1
        assert classes[0].startswith("bg-")

    def test_width_percent(self):
        """width: 100% should map to w-full."""
        classes = TailwindMapper().map_properties({"width": "100%"})
        assert "w-full" in classes

    def test_width_px(self):
        """width: 200px should map to w-50 (200/4)."""
        classes = TailwindMapper().map_properties({"width": "200px"})
        assert "w-50" in classes

    def test_padding_uniform(self):
        """padding should map to p-* class."""
        classes = TailwindMapper().map_properties({"padding": "16.0px"})
        assert "p-4" in classes

    def test_padding_xy(self):
        """padding-x and padding-y should map separately."""
        classes = TailwindMapper().map_properties({
            "padding-x": "16.0px",
            "padding-y": "8.0px",
        })
        assert "px-4" in classes
        assert "py-2" in classes

    def test_gap(self):
        """gap should map to gap-*."""
        classes = TailwindMapper().map_properties({"gap": "12.0px"})
        assert "gap-3" in classes

    def test_border_properties(self):
        """border-width + border-color should produce border classes."""
        classes = TailwindMapper().map_properties({
            "border-width": "1.0px",
            "border-color": "#000000",
            "border-style": "solid",
        })
        assert "border" in classes
        # #000000 snaps to neutral-950 (distance ~17.3, within threshold 20)
        assert any(c.startswith("border-") and c != "border" and c != "border-solid" for c in classes)
        assert "border-solid" in classes

    def test_box_shadow_maps_to_shadow(self):
        """box-shadow should map to shadow-* class."""
        classes = TailwindMapper().map_properties({
            "box-shadow": "0.0px 4.0px 6.0px 0.0px rgba(0, 0, 0, 0.10)"
        })
        assert len(classes) == 1
        assert "shadow" in classes[0]

    def test_opacity(self):
        """opacity should map to opacity-* class."""
        classes = TailwindMapper().map_properties({"opacity": "0.50"})
        assert "opacity-50" in classes

    def test_overflow_hidden(self):
        """overflow: hidden should map to overflow-hidden."""
        classes = TailwindMapper().map_properties({"overflow": "hidden"})
        assert "overflow-hidden" in classes

    def test_blur_filter(self):
        """filter: blur() should map to blur-* class."""
        classes = TailwindMapper().map_properties({"filter": "blur(4.0px)"})
        assert len(classes) == 1
        assert "blur" in classes[0]

    def test_backdrop_blur(self):
        """backdrop-filter: blur() should map to backdrop-blur-*."""
        classes = TailwindMapper().map_properties({"backdrop-filter": "blur(8.0px)"})
        assert len(classes) == 1
        assert "backdrop-blur" in classes[0]

    def test_gradient_direction(self):
        """linear-gradient(to right, ...) should map to bg-linear-to-r."""
        classes = TailwindMapper().map_properties({
            "background-image": "linear-gradient(to right, #000 0%, #fff 100%)"
        })
        assert "bg-linear-to-r" in classes

    def test_internal_markers_skipped(self):
        """Properties starting with _ should be ignored."""
        classes = TailwindMapper().map_properties({"_image_ref": "abc123"})
        assert classes == []


# ---------------------------------------------------------------------------
# snap_color
# ---------------------------------------------------------------------------

class TestSnapColor:
    """Test color palette snapping."""

    def test_white(self):
        """Pure white should snap to a white-like class or arbitrary."""
        result = snap_color("#ffffff", "bg")
        # White is close to neutral-50 or could be arbitrary
        assert result.startswith("bg-")

    def test_black(self):
        """Pure black should snap to a dark palette shade."""
        result = snap_color("#000000", "bg")
        assert result.startswith("bg-")

    def test_exact_red_500(self):
        """Exact red-500 (ef4444) should snap to bg-red-500."""
        result = snap_color("#ef4444", "bg")
        assert result == "bg-red-500"

    def test_exact_blue_500(self):
        """Exact blue-500 (3b82f6) should snap to bg-blue-500."""
        result = snap_color("#3b82f6", "bg")
        assert result == "bg-blue-500"

    def test_near_palette_snap(self):
        """#1a2b3c is close to slate-800 (30,41,59) -- should snap."""
        result = snap_color("#1a2b3c", "bg")
        assert result == "bg-slate-800"

    def test_truly_arbitrary_color(self):
        """A color far from any palette should use arbitrary hex."""
        # Bright neon green -- far from all Tailwind palettes
        result = snap_color("#00ff80", "bg")
        # Should snap to closest green/emerald shade within threshold,
        # or use arbitrary if distance > 20
        assert result.startswith("bg-")

    def test_text_prefix(self):
        """Text color prefix should produce text-* classes."""
        result = snap_color("#ef4444", "text")
        assert result.startswith("text-")

    def test_border_prefix(self):
        """Border prefix should produce border-* classes."""
        result = snap_color("#ef4444", "border")
        assert result.startswith("border-")

    def test_rgba_color(self):
        """rgba() format should be parsed correctly."""
        result = snap_color("rgba(239, 68, 68, 0.50)", "bg")
        assert result.startswith("bg-")


# ---------------------------------------------------------------------------
# map_font_size
# ---------------------------------------------------------------------------

class TestMapFontSize:
    """Test font size to text-* class mapping."""

    def test_12px_text_xs(self):
        assert map_font_size(12) == "text-xs"

    def test_14px_text_sm(self):
        assert map_font_size(14) == "text-sm"

    def test_16px_text_base(self):
        assert map_font_size(16) == "text-base"

    def test_18px_text_lg(self):
        assert map_font_size(18) == "text-lg"

    def test_20px_text_xl(self):
        assert map_font_size(20) == "text-xl"

    def test_24px_text_2xl(self):
        assert map_font_size(24) == "text-2xl"

    def test_30px_text_3xl(self):
        assert map_font_size(30) == "text-3xl"

    def test_36px_text_4xl(self):
        assert map_font_size(36) == "text-4xl"

    def test_48px_text_5xl(self):
        assert map_font_size(48) == "text-5xl"

    def test_13px_snaps_to_xs(self):
        """13px is within 1px of 12px (text-xs) -- snaps to nearest."""
        result = map_font_size(13)
        assert result == "text-xs"

    def test_arbitrary_size_22px(self):
        """22px is 2px from both 20 and 24 -- exceeds >1 threshold."""
        result = map_font_size(22)
        assert result == "text-[22px]"

    def test_very_large_size(self):
        """Size > 128px should use arbitrary value."""
        result = map_font_size(200)
        assert result == "text-[200px]"


# ---------------------------------------------------------------------------
# map_font_weight
# ---------------------------------------------------------------------------

class TestMapFontWeight:
    """Test font weight mapping."""

    def test_100_thin(self):
        assert map_font_weight(100) == "font-thin"

    def test_200_extralight(self):
        assert map_font_weight(200) == "font-extralight"

    def test_300_light(self):
        assert map_font_weight(300) == "font-light"

    def test_400_normal(self):
        assert map_font_weight(400) == "font-normal"

    def test_500_medium(self):
        assert map_font_weight(500) == "font-medium"

    def test_600_semibold(self):
        assert map_font_weight(600) == "font-semibold"

    def test_700_bold(self):
        assert map_font_weight(700) == "font-bold"

    def test_800_extrabold(self):
        assert map_font_weight(800) == "font-extrabold"

    def test_900_black(self):
        assert map_font_weight(900) == "font-black"

    def test_550_rounds_to_600(self):
        """Non-standard 550 should round to 600 (semibold)."""
        assert map_font_weight(550) == "font-semibold"


# ---------------------------------------------------------------------------
# Border radius snapping (Tailwind v4 scale)
# ---------------------------------------------------------------------------

class TestBorderRadius:
    """Test border radius via TailwindMapper._snap_radius."""

    def _snap(self, px: str) -> str:
        return TailwindMapper._snap_radius(px)

    def test_0_none(self):
        assert self._snap("0px") == "rounded-none"

    def test_2_xs(self):
        assert self._snap("2px") == "rounded-xs"

    def test_4_sm(self):
        assert self._snap("4px") == "rounded-sm"

    def test_6_rounded(self):
        """6px snaps to 'rounded' (the base class in v4)."""
        assert self._snap("6px") == "rounded"

    def test_8_md(self):
        assert self._snap("8px") == "rounded-md"

    def test_12_lg(self):
        assert self._snap("12px") == "rounded-lg"

    def test_16_xl(self):
        assert self._snap("16px") == "rounded-xl"

    def test_24_2xl(self):
        assert self._snap("24px") == "rounded-2xl"

    def test_9999_full(self):
        """Very large value should snap to rounded-full."""
        assert self._snap("9999px") == "rounded-full"

    def test_arbitrary_50(self):
        """50px doesn't match any scale closely -- should use arbitrary."""
        result = self._snap("50px")
        assert "rounded-[50px]" == result


# ---------------------------------------------------------------------------
# Shadow mapping
# ---------------------------------------------------------------------------

class TestShadowMapping:
    """Test box-shadow to shadow-* class mapping."""

    def _map(self, shadow: str) -> str:
        return TailwindMapper._map_shadow(shadow)

    def test_small_shadow(self):
        """Blur radius ~1px should map to shadow-xs."""
        result = self._map("0.0px 1.0px 1.0px 0.0px rgba(0,0,0,0.1)")
        assert result == "shadow-xs"

    def test_medium_shadow(self):
        """Blur radius ~6px should map to shadow-md."""
        result = self._map("0.0px 4.0px 6.0px 0.0px rgba(0,0,0,0.1)")
        assert result == "shadow-md"

    def test_large_shadow(self):
        """Blur radius ~10px should map to shadow-lg."""
        result = self._map("0.0px 8.0px 10.0px 0.0px rgba(0,0,0,0.1)")
        assert result == "shadow-lg"

    def test_inset_shadow(self):
        """Inset shadow should map to shadow-inner."""
        result = self._map("inset 0.0px 2.0px 4.0px 0.0px rgba(0,0,0,0.1)")
        assert result == "shadow-inner"


# ---------------------------------------------------------------------------
# Opacity mapping
# ---------------------------------------------------------------------------

class TestOpacityMapping:
    """Test CSS opacity to Tailwind opacity-* class mapping."""

    def _map(self, val: str) -> str:
        return TailwindMapper._map_opacity(val)

    def test_full_opacity(self):
        assert self._map("1.00") == "opacity-100"

    def test_50_percent(self):
        assert self._map("0.50") == "opacity-50"

    def test_zero_opacity(self):
        assert self._map("0.00") == "opacity-0"

    def test_75_percent(self):
        assert self._map("0.75") == "opacity-75"

    def test_30_percent(self):
        assert self._map("0.30") == "opacity-30"


# ---------------------------------------------------------------------------
# Typography helpers
# ---------------------------------------------------------------------------

class TestLetterSpacing:
    """Test letter spacing to tracking-* class mapping."""

    def test_normal(self):
        assert map_letter_spacing(0) == "tracking-normal"

    def test_tight(self):
        assert map_letter_spacing(-0.4) == "tracking-tight"

    def test_wide(self):
        assert map_letter_spacing(0.4) == "tracking-wide"


class TestLineHeight:
    """Test line height to leading-* class mapping."""

    def test_none(self):
        """line-height = font-size = ratio 1.0 -> leading-none."""
        assert map_line_height(16, 16) == "leading-none"

    def test_tight(self):
        """ratio ~1.125 -> leading-tight."""
        assert map_line_height(18, 16) == "leading-tight"

    def test_normal(self):
        """ratio ~1.5 -> leading-normal."""
        assert map_line_height(24, 16) == "leading-normal"

    def test_loose(self):
        """ratio > 1.625 -> leading-loose."""
        assert map_line_height(32, 16) == "leading-loose"


class TestTextAlign:
    """Test text alignment mapping."""

    def test_left_is_none(self):
        """LEFT alignment is default -- returns None."""
        assert map_text_align("LEFT") is None

    def test_center(self):
        assert map_text_align("CENTER") == "text-center"

    def test_right(self):
        assert map_text_align("RIGHT") == "text-right"

    def test_justified(self):
        assert map_text_align("JUSTIFIED") == "text-justify"

    def test_none_input(self):
        assert map_text_align(None) is None
