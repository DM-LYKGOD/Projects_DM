# Load necessary libraries
library(sf)
library(dplyr)
library(mapview)
library(sfnetworks)
library(igraph)
library(tidygraph)
library(ggplot2)

# Define file paths
coordinates_file <- "C:/Users/Debapratim Mukherjee/Downloads/coordinates.csv"
gpk_file <- "C:/Users/Debapratim Mukherjee/Downloads/rivers_rlp.gpkg"

# Read coordinates
coordinate <- read.csv(coordinates_file)
print("Coordinates read successfully")

# Convert coordinates to sf object
crds <- st_as_sf(coordinate, coords = c("longitude", "latitude"), crs = 3035)
print("Coordinates converted to sf object")
print(crds)

# Read river data
river <- st_read(gpk_file)
print("River data read successfully")

# Transform river data
rivers <- st_transform(river, crs = 3035)
print("River data transformed")

# Remove duplicates and cast as LINESTRING
rivers <- rivers %>% distinct() %>% st_cast("LINESTRING")
print("Duplicates removed and data cast to LINESTRING")
print(rivers)

# Create sfnetwork
rivers_net <- as_sfnetwork(rivers, directed = FALSE)
print("sfnetwork created")

# Smooth pseudo nodes of network
rivers_net <- convert(rivers_net, to_spatial_smooth)
print("Pseudo nodes smoothed")

# Process the network
rivers_net <- rivers_net %>%
  activate("nodes") %>%
  st_transform(crs = 3035) %>%
  st_network_blend(crds) %>%
  activate("edges") %>%
  mutate(weight = edge_length())
print("Network processed")

# Calculate distance matrix
dist_mat <- st_network_cost(rivers_net, from = crds, to = crds, weights = "weight")
dist_mat_df <- as.data.frame(as.matrix(dist_mat))
print("Distance matrix calculated")
print(dist_mat_df)

# Plotting of the paths along the river
edge_data <- st_as_sf(rivers_net, "edges")
print("Edge data prepared for plotting")

# Create the base plot
base_plot <- ggplot() +
  geom_sf(data = edge_data, color = "gray", size = 0.5) +
  geom_sf(data = crds, color = "blue", size = 2, shape = 21, fill = "white") +
  theme_minimal()
print("Base plot created")

# Plot all shortest paths between each pair of coordinates
for (i in 1:(nrow(crds) - 1)) {
  for (j in (i + 1):nrow(crds)) {
    path <- st_network_paths(rivers_net, from = crds[i, ], to = crds[j, ], weights = "weight")
    path_edges <- rivers_net %>%
      activate("edges") %>%
      slice(unlist(path$edge_paths)) %>%
      st_as_sf()
    base_plot <- base_plot +
      geom_sf(data = path_edges, color = "red", size = 0.8, alpha = 0.6)
  }
}
print("Paths plotted")

# Print the final plot
print(base_plot)






# Elevation Model
dem <- rast("C:/Users/Debapratim Mukherjee/Downloads/DTM Germany_Rheinland-Pfalz 20m.tif")

get_elevation <- function(x, dem){
  crds <- st_coordinates(x)
  
  crds_df <- data.frame(
    lon = crds[, 1],
    lat = crds[, 2]
  )
  
  crds <- st_as_sf(crds_df,
                   coords = c("lon", "lat"),
                   crs = 3035)
  
  points <- crds[c(1, nrow(crds)), ]
  elevation <- extract(dem, points)
  elevation_diff <- abs(elevation[1, 2] - elevation[2, 2])
  
  return(elevation_diff)
}



# Calculate elevation difference for each edge
results <- edge_data %>%
  rowwise() %>%
  mutate(diff = get_elevation(x = geom, dem = dem))

results$diff[is.na(results$diff)] <- 0

results$weight <- drop_units(results$weight)
results$hyp <- sqrt(results$weight^2 + results$diff^2)


# Plot with river_net$weight as river_net$hyp
rivers_net$weight <- results$hyp

# Calculate distance matrix
dist_mat <- st_network_cost(rivers_net, from = crds, to = crds, weights = "weight")
dist_mat_df <- as.data.frame(as.matrix(dist_mat))
print("Distance matrix calculated")
print(dist_mat_df)

# Plotting of the paths along the river
edge_data <- st_as_sf(rivers_net, "edges")
print("Edge data prepared for plotting")

# Create the base plot
base_plot <- ggplot() +
  geom_sf(data = edge_data, color = "gray", size = 0.5) +
  geom_sf(data = crds, color = "blue", size = 2, shape = 21, fill = "white") +
  theme_minimal()
print("Base plot created")

# Plot all shortest paths between each pair of coordinates
for (i in 1:(nrow(crds) - 1)) {
  for (j in (i + 1):nrow(crds)) {
    path <- st_network_paths(rivers_net, from = crds[i, ], to = crds[j, ], weights = "weight")
    path_edges <- rivers_net %>%
      activate("edges") %>%
      slice(unlist(path$edge_paths)) %>%
      st_as_sf()
    base_plot <- base_plot +
      geom_sf(data = path_edges, color = "orange", size = 0.8, alpha = 0.6)
  }
}
print("Paths plotted")

# Print the final plot
print(base_plot)
