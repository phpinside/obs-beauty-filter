/*
 * obs-beauty-filter —— OBS 原生美颜滤镜
 *
 * 与“BeautyCam 虚拟摄像头”方案的区别：这个插件直接作为滤镜挂在任意视频源上
 * （视频采集设备 / 媒体源 / 窗口采集），不需要额外的外部进程。
 *
 * 算法全部在 GLSL 里完成，不依赖任何商业美颜 SDK：
 *   1) 肤色掩膜（避免把人脸以外的东西一起磨）
 *   2) 保边加权模糊 -> 磨皮
 *   3) 提亮 + 暖调 -> 美白 / 红润
 *   4) 非皮肤区 USM -> 锐化，找回五官细节
 *   5) 椭圆向心变形 -> 瘦脸（可选手动框）
 */
#include <obs-module.h>
#include <graphics/graphics.h>
#include <graphics/vec2.h>
#include <graphics/vec4.h>
#include <util/platform.h>

#include "beauty-filter.h"

#define SETTING_SMOOTH "smooth"
#define SETTING_WHITEN "whiten"
#define SETTING_ROSY "rosy"
#define SETTING_SHARPEN "sharpen"
#define SETTING_SLIM "slim"
#define SETTING_FACE_X "face_x"
#define SETTING_FACE_Y "face_y"
#define SETTING_FACE_RX "face_rx"
#define SETTING_FACE_RY "face_ry"
#define SETTING_ENABLED "enabled"

static const char *bf_name(void *unused)
{
	UNUSED_PARAMETER(unused);
	return obs_module_text("BeautyFilter.Name");
}

static void bf_update(void *data, obs_data_t *settings)
{
	struct beauty_filter *f = data;

	f->enabled = obs_data_get_bool(settings, SETTING_ENABLED);
	f->smooth = (float)obs_data_get_double(settings, SETTING_SMOOTH);
	f->whiten = (float)obs_data_get_double(settings, SETTING_WHITEN);
	f->rosy = (float)obs_data_get_double(settings, SETTING_ROSY);
	f->sharpen = (float)obs_data_get_double(settings, SETTING_SHARPEN);
	f->slim = (float)obs_data_get_double(settings, SETTING_SLIM);
	f->face_x = (float)obs_data_get_double(settings, SETTING_FACE_X);
	f->face_y = (float)obs_data_get_double(settings, SETTING_FACE_Y);
	f->face_rx = (float)obs_data_get_double(settings, SETTING_FACE_RX);
	f->face_ry = (float)obs_data_get_double(settings, SETTING_FACE_RY);
}

static void *bf_create(obs_data_t *settings, obs_source_t *context)
{
	struct beauty_filter *f = bzalloc(sizeof(struct beauty_filter));
	f->context = context;

	char *path = obs_module_file("shaders/beauty.effect");
	obs_enter_graphics();
	f->effect = gs_effect_create_from_file(path, NULL);
	obs_leave_graphics();
	bfree(path);

	if (!f->effect) {
		blog(LOG_ERROR, "[beauty-filter] 无法加载 shaders/beauty.effect，请检查 data 目录");
	} else {
		f->p_smooth = gs_effect_get_param_by_name(f->effect, "smoothAmount");
		f->p_whiten = gs_effect_get_param_by_name(f->effect, "whitenAmount");
		f->p_rosy = gs_effect_get_param_by_name(f->effect, "rosyAmount");
		f->p_sharpen = gs_effect_get_param_by_name(f->effect, "sharpenAmount");
		f->p_slim = gs_effect_get_param_by_name(f->effect, "slimAmount");
		f->p_texel = gs_effect_get_param_by_name(f->effect, "texel");
		f->p_face = gs_effect_get_param_by_name(f->effect, "faceRect");
	}

	bf_update(f, settings);
	return f;
}

static void bf_destroy(void *data)
{
	struct beauty_filter *f = data;
	if (f->effect) {
		obs_enter_graphics();
		gs_effect_destroy(f->effect);
		obs_leave_graphics();
	}
	bfree(f);
}

static void bf_get_defaults(obs_data_t *settings)
{
	obs_data_set_default_bool(settings, SETTING_ENABLED, true);
	obs_data_set_default_double(settings, SETTING_SMOOTH, 0.55);
	obs_data_set_default_double(settings, SETTING_WHITEN, 0.30);
	obs_data_set_default_double(settings, SETTING_ROSY, 0.20);
	obs_data_set_default_double(settings, SETTING_SHARPEN, 0.30);
	obs_data_set_default_double(settings, SETTING_SLIM, 0.00);
	obs_data_set_default_double(settings, SETTING_FACE_X, 0.50);
	obs_data_set_default_double(settings, SETTING_FACE_Y, 0.46);
	obs_data_set_default_double(settings, SETTING_FACE_RX, 0.22);
	obs_data_set_default_double(settings, SETTING_FACE_RY, 0.30);
}

static obs_properties_t *bf_properties(void *data)
{
	UNUSED_PARAMETER(data);
	obs_properties_t *p = obs_properties_create();

	obs_properties_add_bool(p, SETTING_ENABLED, obs_module_text("BeautyFilter.Enabled"));

	obs_properties_add_float_slider(p, SETTING_SMOOTH, obs_module_text("BeautyFilter.Smooth"),
					0.0, 1.0, 0.01);
	obs_properties_add_float_slider(p, SETTING_WHITEN, obs_module_text("BeautyFilter.Whiten"),
					0.0, 1.0, 0.01);
	obs_properties_add_float_slider(p, SETTING_ROSY, obs_module_text("BeautyFilter.Rosy"),
					0.0, 1.0, 0.01);
	obs_properties_add_float_slider(p, SETTING_SHARPEN, obs_module_text("BeautyFilter.Sharpen"),
					0.0, 1.0, 0.01);

	obs_properties_t *geo = obs_properties_create();
	obs_properties_add_float_slider(geo, SETTING_SLIM, obs_module_text("BeautyFilter.Slim"),
					-0.6, 0.6, 0.01);
	obs_properties_add_float_slider(geo, SETTING_FACE_X, obs_module_text("BeautyFilter.FaceX"),
					0.0, 1.0, 0.005);
	obs_properties_add_float_slider(geo, SETTING_FACE_Y, obs_module_text("BeautyFilter.FaceY"),
					0.0, 1.0, 0.005);
	obs_properties_add_float_slider(geo, SETTING_FACE_RX, obs_module_text("BeautyFilter.FaceRX"),
					0.05, 0.6, 0.005);
	obs_properties_add_float_slider(geo, SETTING_FACE_RY, obs_module_text("BeautyFilter.FaceRY"),
					0.05, 0.6, 0.005);
	obs_properties_add_group(p, "geometry", obs_module_text("BeautyFilter.Geometry"),
				 OBS_GROUP_NORMAL, geo);

	return p;
}

static void bf_video_render(void *data, gs_effect_t *effect)
{
	struct beauty_filter *f = data;

	if (!f->effect || !f->enabled) {
		obs_source_skip_video_filter(f->context);
		return;
	}

	if (!obs_source_process_filter_begin(f->context, GS_RGBA, OBS_ALLOW_DIRECT_RENDERING))
		return;

	uint32_t w = obs_source_get_width(f->context);
	uint32_t h = obs_source_get_height(f->context);
	if (!w || !h) {
		obs_source_process_filter_end(f->context, f->effect, 0, 0);
		return;
	}

	struct vec2 texel;
	vec2_set(&texel, 1.0f / (float)w, 1.0f / (float)h);
	gs_effect_set_vec2(f->p_texel, &texel);

	struct vec4 face;
	vec4_set(&face, f->face_x, f->face_y, f->face_rx, f->face_ry);
	gs_effect_set_vec4(f->p_face, &face);

	gs_effect_set_float(f->p_smooth, f->smooth);
	gs_effect_set_float(f->p_whiten, f->whiten);
	gs_effect_set_float(f->p_rosy, f->rosy);
	gs_effect_set_float(f->p_sharpen, f->sharpen);
	gs_effect_set_float(f->p_slim, f->slim);

	obs_source_process_filter_end(f->context, f->effect, w, h);
	UNUSED_PARAMETER(effect);
}

struct obs_source_info beauty_filter_info = {
	.id = "beauty_filter",
	.type = OBS_SOURCE_TYPE_FILTER,
	.output_flags = OBS_SOURCE_VIDEO,
	.get_name = bf_name,
	.create = bf_create,
	.destroy = bf_destroy,
	.update = bf_update,
	.get_defaults = bf_get_defaults,
	.get_properties = bf_properties,
	.video_render = bf_video_render,
};
