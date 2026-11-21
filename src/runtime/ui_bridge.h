/**
 * ui_bridge.h - Native Screen, Touch & Graphics Proxy Bridge
 * Part of Arm32Runner Jailbreak Tweak for Sileo
 */

#ifndef UI_BRIDGE_H
#define UI_BRIDGE_H

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    float width;
    float height;
    float scale;
    bool is_retina;
    bool aspect_fill;
} DisplayMetrics;

typedef struct {
    uint32_t touch_type; // 0: down, 1: moved, 2: up, 3: cancelled
    float x;
    float y;
    uint32_t timestamp_ms;
} TouchEvent32;

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Calculates scaling matrix from legacy resolution (e.g. 320x480, 640x960, 640x1136)
 * to modern iPhone screens (e.g. iPhone 11/12/13/14/15/16 OLED resolutions).
 */
void ui_bridge_calc_viewport(float src_w, float src_h, float screen_w, float screen_h, DisplayMetrics *out_metrics);

/**
 * Translates modern touch coordinates back into 32-bit application coordinate system.
 */
void ui_bridge_translate_touch(const DisplayMetrics *metrics, float screen_x, float screen_y, float *out_app_x, float *out_app_y);

#ifdef __cplusplus
}
#endif

#endif /* UI_BRIDGE_H */
