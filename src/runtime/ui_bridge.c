/**
 * ui_bridge.c - Native Screen, Touch & Graphics Proxy Bridge Implementation
 * Part of Arm32Runner Jailbreak Tweak for Sileo
 */

#include "ui_bridge.h"
#include <string.h>

void ui_bridge_calc_viewport(float src_w, float src_h, float screen_w, float screen_h, DisplayMetrics *out_metrics) {
    if (!out_metrics) return;
    memset(out_metrics, 0, sizeof(DisplayMetrics));

    if (src_w <= 0.0f) src_w = 320.0f;
    if (src_h <= 0.0f) src_h = 480.0f;

    float scale_x = screen_w / src_w;
    float scale_y = screen_h / src_h;

    // Use uniform aspect ratio fitting
    float uniform_scale = (scale_x < scale_y) ? scale_x : scale_y;

    out_metrics->width = src_w * uniform_scale;
    out_metrics->height = src_h * uniform_scale;
    out_metrics->scale = uniform_scale;
    out_metrics->is_retina = (uniform_scale >= 2.0f);
    out_metrics->aspect_fill = false;
}

void ui_bridge_translate_touch(const DisplayMetrics *metrics, float screen_x, float screen_y, float *out_app_x, float *out_app_y) {
    if (!metrics || !out_app_x || !out_app_y || metrics->scale <= 0.0f) return;

    *out_app_x = screen_x / metrics->scale;
    *out_app_y = screen_y / metrics->scale;
}
