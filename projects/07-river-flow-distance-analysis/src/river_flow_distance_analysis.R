library(sf)
library(dplyr)
library(ggplot2)
library(sfnetworks)
library(tidygraph)
library(igraph)
library(terra)
library(units)


get_project_root <- function() {
  file_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
  if (length(file_arg) == 0) {
    return(normalizePath(".", winslash = "/", mustWork = FALSE))
  }

  script_path <- sub("^--file=", "", file_arg[1])
  normalizePath(file.path(dirname(script_path), ".."), winslash = "/", mustWork = FALSE)
}


read_inputs <- function(data_dir) {
  coordinates_path <- file.path(data_dir, "coordinates.csv")
  rivers_path <- file.path(data_dir, "rivers_rlp.gpkg")
  dem_path <- file.path(data_dir, "dtm_germany_rheinland_pfalz_20m.tif")

  if (!file.exists(coordinates_path)) {
    stop("Missing coordinates file: ", coordinates_path)
  }
  if (!file.exists(rivers_path)) {
    stop("Missing river network file: ", rivers_path)
  }
  if (!file.exists(dem_path)) {
    stop("Missing DEM file: ", dem_path)
  }

  coordinates <- read.csv(coordinates_path)
  points <- st_as_sf(coordinates, coords = c("longitude", "latitude"), crs = 3035)
  rivers <- st_read(rivers_path, quiet = TRUE) %>%
    st_transform(crs = 3035) %>%
    distinct() %>%
    st_cast("LINESTRING")

  list(points = points, rivers = rivers, dem = rast(dem_path))
}


build_network <- function(rivers, points) {
  as_sfnetwork(rivers, directed = FALSE) %>%
    convert(to_spatial_smooth) %>%
    activate("nodes") %>%
    st_transform(crs = 3035) %>%
    st_network_blend(points) %>%
    activate("edges") %>%
    mutate(weight = edge_length())
}


calculate_distance_matrix <- function(network, points) {
  st_network_cost(network, from = points, to = points, weights = "weight") %>%
    as.matrix() %>%
    as.data.frame()
}


collect_shortest_path_edges <- function(network, points) {
  edge_indices <- integer()
  for (i in seq_len(nrow(points) - 1)) {
    for (j in seq((i + 1), nrow(points))) {
      path <- st_network_paths(network, from = points[i, ], to = points[j, ], weights = "weight")
      edge_indices <- c(edge_indices, unlist(path$edge_paths))
    }
  }

  edge_indices <- unique(edge_indices[edge_indices > 0])
  network %>%
    activate("edges") %>%
    slice(edge_indices) %>%
    st_as_sf()
}


plot_shortest_paths <- function(network, points, path_color, title) {
  edge_data <- st_as_sf(network, "edges")
  path_edges <- collect_shortest_path_edges(network, points)

  ggplot() +
    geom_sf(data = edge_data, color = "gray70", linewidth = 0.5) +
    geom_sf(data = path_edges, color = path_color, linewidth = 0.8, alpha = 0.7) +
    geom_sf(data = points, color = "navy", size = 2.5, shape = 21, fill = "white") +
    labs(title = title) +
    theme_minimal()
}


get_elevation_difference <- function(geometry, dem) {
  coords <- st_coordinates(geometry)
  coords_df <- data.frame(x = coords[, 1], y = coords[, 2])
  points <- st_as_sf(coords_df, coords = c("x", "y"), crs = 3035)
  endpoints <- points[c(1, nrow(points)), ]
  elevation <- terra::extract(dem, terra::vect(endpoints))

  if (nrow(elevation) < 2) {
    return(0)
  }

  abs(elevation[1, 2] - elevation[2, 2])
}


apply_elevation_weights <- function(network, dem) {
  edge_data <- st_as_sf(network, "edges")
  weighted_edges <- edge_data %>%
    rowwise() %>%
    mutate(
      elevation_diff = get_elevation_difference(geometry, dem),
      planar_weight = units::drop_units(weight),
      weight = sqrt(planar_weight^2 + elevation_diff^2)
    ) %>%
    ungroup()

  network %>%
    activate("edges") %>%
    mutate(weight = weighted_edges$weight)
}


write_outputs <- function(distance_df, plot_object, output_dir, stem) {
  if (!dir.exists(output_dir)) {
    dir.create(output_dir, recursive = TRUE)
  }

  write.csv(distance_df, file.path(output_dir, paste0(stem, "_distance_matrix.csv")), row.names = FALSE)
  ggsave(
    filename = file.path(output_dir, paste0(stem, "_paths.png")),
    plot = plot_object,
    width = 10,
    height = 7,
    dpi = 300
  )
}


project_root <- get_project_root()
data_dir <- file.path(project_root, "data")
output_dir <- file.path(project_root, "outputs")

inputs <- read_inputs(data_dir)
river_network <- build_network(inputs$rivers, inputs$points)

planar_distances <- calculate_distance_matrix(river_network, inputs$points)
planar_plot <- plot_shortest_paths(
  network = river_network,
  points = inputs$points,
  path_color = "red",
  title = "Shortest Paths Along the River Network"
)
print(planar_distances)
print(planar_plot)
write_outputs(planar_distances, planar_plot, output_dir, "planar")

terrain_network <- apply_elevation_weights(river_network, inputs$dem)
terrain_distances <- calculate_distance_matrix(terrain_network, inputs$points)
terrain_plot <- plot_shortest_paths(
  network = terrain_network,
  points = inputs$points,
  path_color = "orange",
  title = "Terrain-Adjusted Shortest Paths Along the River Network"
)
print(terrain_distances)
print(terrain_plot)
write_outputs(terrain_distances, terrain_plot, output_dir, "terrain_adjusted")
