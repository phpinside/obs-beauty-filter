cmake_minimum_required(VERSION 3.20)
project(obs-beauty-filter VERSION 1.0.0 LANGUAGES C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# 两种构建方式都支持：
#   A) 作为子目录放进 obs-studio/plugins/ 里（推荐，最省事，OBS 的 cmake 宏直接可用）
#   B) 独立构建：cmake -S . -B build -Dlibobs_DIR=<obs build 目录>
if(NOT TARGET OBS::libobs)
  find_package(libobs REQUIRED)
endif()

add_library(obs-beauty-filter MODULE
  src/plugin-main.c
  src/beauty-filter.c)

target_include_directories(obs-beauty-filter PRIVATE src)
target_link_libraries(obs-beauty-filter PRIVATE OBS::libobs)

set_target_properties(obs-beauty-filter PROPERTIES
  PREFIX ""
  FOLDER "plugins"
  OUTPUT_NAME "obs-beauty-filter")

if(COMMAND install_obs_plugin_with_data)
  install_obs_plugin_with_data(obs-beauty-filter data)
else()
  # 独立构建时的安装布局，与 OBS 官方插件保持一致
  install(TARGETS obs-beauty-filter
          RUNTIME DESTINATION "obs-plugins/64bit"
          LIBRARY DESTINATION "obs-plugins/64bit")
  install(DIRECTORY data/ DESTINATION "data/obs-plugins/obs-beauty-filter")
endif()
