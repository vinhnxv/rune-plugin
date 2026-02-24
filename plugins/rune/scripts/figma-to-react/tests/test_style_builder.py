"""Tests for style_builder.py — Builder pattern for CSS property extraction."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from style_builder import StyleBuilder  # noqa: E402
from figma_types import Color, Effect, EffectType, Paint, PaintType, Vector2D  # noqa: E402


# ---------------------------------------------------------------------------
# Chainable methods
# ---------------------------------------------------------------------------

class TestChainableMethods:
    """Test that StyleBuilder supports method chaining."""

    def test_chaining_returns_self(self):
        """Each builder method should return self for chaining."""
        builder = StyleBuilder()
        result = builder.size(100, 50)
        assert result is builder

    def test_multi_chain(self):
        """Multiple chained calls should accumulate properties."""
        props = (
            StyleBuilder()
            .size(100, 50)
            .corner_radius(8)
            .opacity(0.5)
            .build()
        )
        assert isinstance(props, dict)
        assert "width" in props
        assert "border-radius" in props
        assert "opacity" in props

    def test_empty_builder(self):
        """Empty builder should produce empty dict."""
        result = StyleBuilder().build()
        assert result == {}


# ---------------------------------------------------------------------------
# Fill extraction
# ---------------------------------------------------------------------------

class TestFills:
    """Test fill style extraction."""

    def _solid_paint(self, r: float, g: float, b: float, a: float = 1.0,
                     visible: bool = True) -> Paint:
        """Helper to create a solid Paint."""
        return Paint(
            type=PaintType.SOLID,
            visible=visible,
            opacity=1.0,
            color=Color(r=r, g=g, b=b, a=a),
        )

    def test_solid_fill_white(self):
        """White solid fill should set background-color."""
        props = StyleBuilder().fills([self._solid_paint(1.0, 1.0, 1.0)]).build()
        assert "background-color" in props
        assert props["background-color"] == "#ffffff"

    def test_solid_fill_black(self):
        """Black solid fill should set background-color."""
        props = StyleBuilder().fills([self._solid_paint(0.0, 0.0, 0.0)]).build()
        assert props["background-color"] == "#000000"

    def test_solid_fill_with_alpha(self):
        """Color with alpha < 1.0 should produce rgba()."""
        props = StyleBuilder().fills([self._solid_paint(1.0, 0.0, 0.0, a=0.5)]).build()
        assert "background-color" in props
        assert "rgba(" in props["background-color"]

    def test_invisible_fill_ignored(self):
        """Fills with visible=false should be ignored."""
        props = StyleBuilder().fills(
            [self._solid_paint(1.0, 0.0, 0.0, visible=False)]
        ).build()
        assert "background-color" not in props

    def test_gradient_fill(self):
        """Gradient fills should produce background-image."""
        paint = Paint.model_validate({
            "type": "GRADIENT_LINEAR",
            "visible": True,
            "opacity": 1.0,
            "gradientHandlePositions": [
                {"x": 0.0, "y": 0.5},
                {"x": 1.0, "y": 0.5},
            ],
            "gradientStops": [],
        })
        props = StyleBuilder().fills([paint]).build()
        assert "background-image" in props
        assert "linear-gradient" in props["background-image"]

    def test_gradient_direction_to_right(self):
        """Horizontal gradient (left->right) should produce 'to right' direction."""
        paint = Paint.model_validate({
            "type": "GRADIENT_LINEAR",
            "visible": True,
            "opacity": 1.0,
            "gradientHandlePositions": [
                {"x": 0.0, "y": 0.5},
                {"x": 1.0, "y": 0.5},
            ],
            "gradientStops": [],
        })
        props = StyleBuilder().fills([paint]).build()
        assert "to right" in props["background-image"]

    def test_image_fill(self):
        """IMAGE fills should set background-size and position."""
        paint = Paint.model_validate({
            "type": "IMAGE",
            "visible": True,
            "opacity": 1.0,
            "imageRef": "abc123",
        })
        props = StyleBuilder().fills([paint]).build()
        assert props.get("background-size") == "cover"
        assert props.get("background-position") == "center"
        assert props.get("_image_ref") == "abc123"

    def test_empty_fills(self):
        """Empty fills list should produce no background properties."""
        props = StyleBuilder().fills([]).build()
        assert "background-color" not in props
        assert "background-image" not in props

    def test_multiple_fills_uses_first_visible(self):
        """Only the first visible fill should be used."""
        fills = [
            self._solid_paint(1.0, 0.0, 0.0, visible=False),  # invisible red
            self._solid_paint(0.0, 1.0, 0.0),  # visible green
            self._solid_paint(0.0, 0.0, 1.0),  # visible blue (ignored)
        ]
        props = StyleBuilder().fills(fills).build()
        # Should use green (second fill, first visible)
        assert "background-color" in props
        assert "00ff00" in props["background-color"].lower()


# ---------------------------------------------------------------------------
# Stroke extraction
# ---------------------------------------------------------------------------

class TestStrokes:
    """Test stroke style extraction."""

    def test_single_stroke(self):
        """Single stroke should produce border properties."""
        paint = Paint(
            type=PaintType.SOLID,
            visible=True,
            opacity=1.0,
            color=Color(r=0.0, g=0.0, b=0.0, a=1.0),
        )
        props = StyleBuilder().strokes([paint], weight=1.0).build()
        assert props.get("border-width") == "1.0px"
        assert props.get("border-style") == "solid"
        assert "border-color" in props

    def test_thick_stroke(self):
        """Stroke weight 2 should produce border-width: 2px."""
        paint = Paint(
            type=PaintType.SOLID,
            visible=True,
            opacity=1.0,
            color=Color(r=0.0, g=0.0, b=0.0, a=1.0),
        )
        props = StyleBuilder().strokes([paint], weight=2.0).build()
        assert props["border-width"] == "2.0px"

    def test_zero_weight_no_border(self):
        """Zero weight should produce no border properties."""
        paint = Paint(
            type=PaintType.SOLID,
            visible=True,
            opacity=1.0,
            color=Color(r=0.0, g=0.0, b=0.0, a=1.0),
        )
        props = StyleBuilder().strokes([paint], weight=0).build()
        assert "border-width" not in props

    def test_no_strokes(self):
        """Empty strokes should produce no border properties."""
        props = StyleBuilder().strokes([], weight=1.0).build()
        assert "border-width" not in props


# ---------------------------------------------------------------------------
# Effect extraction (shadows, blur)
# ---------------------------------------------------------------------------

class TestEffects:
    """Test effect style extraction."""

    def test_drop_shadow(self):
        """DROP_SHADOW should produce box-shadow."""
        effect = Effect(
            type=EffectType.DROP_SHADOW,
            visible=True,
            radius=6.0,
            color=Color(r=0.0, g=0.0, b=0.0, a=0.1),
            offset=Vector2D(x=0.0, y=4.0),
            spread=0.0,
        )
        props = StyleBuilder().effects([effect]).build()
        assert "box-shadow" in props
        assert "6.0px" in props["box-shadow"]

    def test_inner_shadow(self):
        """INNER_SHADOW should produce inset box-shadow."""
        effect = Effect(
            type=EffectType.INNER_SHADOW,
            visible=True,
            radius=4.0,
            color=Color(r=0.0, g=0.0, b=0.0, a=0.25),
            offset=Vector2D(x=0.0, y=2.0),
            spread=0.0,
        )
        props = StyleBuilder().effects([effect]).build()
        assert "box-shadow" in props
        assert "inset" in props["box-shadow"]

    def test_layer_blur(self):
        """LAYER_BLUR should produce filter: blur()."""
        effect = Effect(
            type=EffectType.LAYER_BLUR,
            visible=True,
            radius=4.0,
        )
        props = StyleBuilder().effects([effect]).build()
        assert props.get("filter") == "blur(4.0px)"

    def test_background_blur(self):
        """BACKGROUND_BLUR should produce backdrop-filter."""
        effect = Effect(
            type=EffectType.BACKGROUND_BLUR,
            visible=True,
            radius=8.0,
        )
        props = StyleBuilder().effects([effect]).build()
        assert props.get("backdrop-filter") == "blur(8.0px)"

    def test_invisible_effect_ignored(self):
        """Invisible effects should be skipped."""
        effect = Effect(
            type=EffectType.DROP_SHADOW,
            visible=False,
            radius=20.0,
            color=Color(r=0.0, g=0.0, b=0.0, a=0.5),
            offset=Vector2D(x=0.0, y=10.0),
            spread=0.0,
        )
        props = StyleBuilder().effects([effect]).build()
        assert "box-shadow" not in props

    def test_multiple_shadows_combined(self):
        """Multiple visible shadows should be comma-separated."""
        effects = [
            Effect(
                type=EffectType.DROP_SHADOW,
                visible=True,
                radius=4.0,
                color=Color(r=0.0, g=0.0, b=0.0, a=0.1),
                offset=Vector2D(x=0.0, y=2.0),
                spread=0.0,
            ),
            Effect(
                type=EffectType.DROP_SHADOW,
                visible=True,
                radius=10.0,
                color=Color(r=0.0, g=0.0, b=0.0, a=0.2),
                offset=Vector2D(x=0.0, y=8.0),
                spread=0.0,
            ),
        ]
        props = StyleBuilder().effects(effects).build()
        assert "box-shadow" in props
        assert "," in props["box-shadow"]

    def test_no_effects(self):
        """Empty effects should produce no shadow/blur properties."""
        props = StyleBuilder().effects([]).build()
        assert "box-shadow" not in props
        assert "filter" not in props


# ---------------------------------------------------------------------------
# Padding optimization
# ---------------------------------------------------------------------------

class TestPadding:
    """Test smart padding optimization."""

    def test_all_equal_padding(self):
        """All 4 sides equal should produce single padding value."""
        props = StyleBuilder().padding((16.0, 16.0, 16.0, 16.0)).build()
        assert props.get("padding") == "16.0px"
        assert "padding-x" not in props

    def test_horizontal_vertical_padding(self):
        """H and V equal but different should produce padding-x/padding-y."""
        props = StyleBuilder().padding((8.0, 16.0, 8.0, 16.0)).build()
        assert props.get("padding-x") == "16.0px"
        assert props.get("padding-y") == "8.0px"
        assert "padding" not in props or props.get("padding") is None

    def test_all_different_padding(self):
        """All different should produce individual padding properties."""
        props = StyleBuilder().padding((4.0, 8.0, 12.0, 16.0)).build()
        assert "padding-top" in props
        assert "padding-right" in props
        assert "padding-bottom" in props
        assert "padding-left" in props

    def test_zero_padding(self):
        """Zero padding should produce no padding properties."""
        props = StyleBuilder().padding((0.0, 0.0, 0.0, 0.0)).build()
        assert "padding" not in props
        assert "padding-top" not in props


# ---------------------------------------------------------------------------
# Corner radius
# ---------------------------------------------------------------------------

class TestCornerRadius:
    """Test corner radius extraction."""

    def test_uniform_radius(self):
        """Uniform radius should produce single border-radius."""
        props = StyleBuilder().corner_radius(8.0).build()
        assert props.get("border-radius") == "8.0px"

    def test_zero_radius(self):
        """Zero radius should produce no border-radius."""
        props = StyleBuilder().corner_radius(0.0).build()
        assert "border-radius" not in props

    def test_per_corner_radius(self):
        """Per-corner radii should produce space-separated values."""
        props = StyleBuilder().corner_radius(0, per_corner=[8, 8, 0, 0]).build()
        assert "border-radius" in props
        assert "8px" in props["border-radius"]
        assert "0px" in props["border-radius"]

    def test_per_corner_all_zero(self):
        """Per-corner all zero should produce no border-radius."""
        props = StyleBuilder().corner_radius(0, per_corner=[0, 0, 0, 0]).build()
        assert "border-radius" not in props


# ---------------------------------------------------------------------------
# Opacity
# ---------------------------------------------------------------------------

class TestOpacity:
    """Test opacity extraction."""

    def test_full_opacity(self):
        """Opacity 1.0 should produce no opacity property."""
        props = StyleBuilder().opacity(1.0).build()
        assert "opacity" not in props

    def test_half_opacity(self):
        """Opacity 0.5 should produce opacity: 0.50."""
        props = StyleBuilder().opacity(0.5).build()
        assert props.get("opacity") == "0.50"

    def test_zero_opacity(self):
        """Opacity 0.0 should produce opacity: 0.00."""
        props = StyleBuilder().opacity(0.0).build()
        assert props.get("opacity") == "0.00"


# ---------------------------------------------------------------------------
# Size
# ---------------------------------------------------------------------------

class TestSize:
    """Test size dimension extraction."""

    def test_fixed_size(self):
        """Fixed dimensions should produce width/height in pixels."""
        props = StyleBuilder().size(400, 300).build()
        assert props.get("width") == "400px"
        assert props.get("height") == "300px"

    def test_fill_sizing(self):
        """FILL sizing should produce width: 100%."""
        props = StyleBuilder().size(400, 300, sizing_h="FILL").build()
        assert props.get("width") == "100%"

    def test_hug_sizing(self):
        """HUG sizing should omit the dimension (auto)."""
        props = StyleBuilder().size(400, 300, sizing_h="HUG", sizing_v="HUG").build()
        assert "width" not in props
        assert "height" not in props

    def test_zero_dimensions(self):
        """Zero dimensions should produce no width/height."""
        props = StyleBuilder().size(0, 0).build()
        assert "width" not in props
        assert "height" not in props


# ---------------------------------------------------------------------------
# Gap
# ---------------------------------------------------------------------------

class TestGap:
    """Test gap property extraction."""

    def test_positive_gap(self):
        """Positive gap should produce gap property."""
        props = StyleBuilder().gap(12.0).build()
        assert props.get("gap") == "12.0px"

    def test_zero_gap(self):
        """Zero gap should produce no gap property."""
        props = StyleBuilder().gap(0).build()
        assert "gap" not in props


# ---------------------------------------------------------------------------
# Min/max constraints
# ---------------------------------------------------------------------------

class TestMinMax:
    """Test min/max dimension constraints."""

    def test_min_width(self):
        """min_w should produce min-width."""
        props = StyleBuilder().min_max(min_w=200).build()
        assert props.get("min-width") == "200px"

    def test_max_width(self):
        """max_w should produce max-width."""
        props = StyleBuilder().min_max(max_w=600).build()
        assert props.get("max-width") == "600px"

    def test_none_values_ignored(self):
        """None values should produce no min/max properties."""
        props = StyleBuilder().min_max().build()
        assert "min-width" not in props
        assert "max-width" not in props


# ---------------------------------------------------------------------------
# Overflow
# ---------------------------------------------------------------------------

class TestOverflow:
    """Test overflow_hidden property."""

    def test_clips_content_true(self):
        """clips=True should produce overflow: hidden."""
        props = StyleBuilder().overflow_hidden(True).build()
        assert props.get("overflow") == "hidden"

    def test_clips_content_false(self):
        """clips=False should produce no overflow property."""
        props = StyleBuilder().overflow_hidden(False).build()
        assert "overflow" not in props


# ---------------------------------------------------------------------------
# Combined builder
# ---------------------------------------------------------------------------

class TestCombinedBuilder:
    """Test full builder pipeline with multiple properties."""

    def test_card_like_styles(self):
        """Build styles for a card-like FRAME node."""
        fills = [Paint(
            type=PaintType.SOLID,
            visible=True,
            opacity=1.0,
            color=Color(r=1.0, g=1.0, b=1.0, a=1.0),
        )]
        effects = [Effect(
            type=EffectType.DROP_SHADOW,
            visible=True,
            radius=6.0,
            color=Color(r=0.0, g=0.0, b=0.0, a=0.1),
            offset=Vector2D(x=0.0, y=4.0),
            spread=0.0,
        )]
        props = (
            StyleBuilder()
            .fills(fills)
            .effects(effects)
            .corner_radius(8.0)
            .padding((16.0, 16.0, 16.0, 16.0))
            .overflow_hidden(True)
            .build()
        )
        assert "background-color" in props
        assert "box-shadow" in props
        assert "border-radius" in props
        assert "padding" in props
        assert props.get("overflow") == "hidden"

    def test_build_is_idempotent(self):
        """Calling build() multiple times should return equal dicts."""
        builder = StyleBuilder().size(100, 50).corner_radius(8)
        result1 = builder.build()
        result2 = builder.build()
        assert result1 == result2
