#include <obs-module.h>

OBS_DECLARE_MODULE()
OBS_MODULE_USE_DEFAULT_LOCALE("obs-beauty-filter", "en-US")

#define BEAUTY_FILTER_VERSION "1.0.0"

extern struct obs_source_info beauty_filter_info;

bool obs_module_load(void)
{
	obs_register_source(&beauty_filter_info);
	blog(LOG_INFO, "[beauty-filter] loaded v%s", BEAUTY_FILTER_VERSION);
	return true;
}

void obs_module_unload(void)
{
	blog(LOG_INFO, "[beauty-filter] unloaded");
}
