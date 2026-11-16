#pragma once

#include <obs-module.h>

struct beauty_filter {
	obs_source_t *context;
	gs_effect_t *effect;

	gs_eparam_t *p_smooth;
	gs_eparam_t *p_whiten;
	gs_eparam_t *p_rosy;
	gs_eparam_t *p_sharpen;
	gs_eparam_t *p_slim;
	gs_eparam_t *p_texel;
	gs_eparam_t *p_face;

	bool enabled;
	float smooth;
	float whiten;
	float rosy;
	float sharpen;
	float slim;
	float face_x;
	float face_y;
	float face_rx;
	float face_ry;
};

extern struct obs_source_info beauty_filter_info;
