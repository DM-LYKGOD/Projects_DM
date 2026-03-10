# Load necessary libraries
library(deSolve)    # For solving differential equations
library(ggplot2)    # For visualization

# Define the model parameters
n_species <- 50      # Number of species
r <- runif(n_species, 0.1, 1)  # Intrinsic growth rates for each species
sigma <- 0.5         # Width of the competition kernel
trait <- runif(n_species, 0, 10)  # Traits for each species
T_baseline <- 1      # Baseline temperature
T_warming <- 1.5     # Warming scenario temperature

# Competition kernel function (Gaussian kernel with temperature dependence)
predation_kernel <- function(T, trait_i, trait_j, sigma) {
  beta_T <- 1 + (T - 1)  # Linear dependence of predation efficiency on temperature
  beta_T * exp(-((trait_i - trait_j)^2) / (2 * sigma^2))
}

# Model differential equations
limiting_similarity_model <- function(time, N, params) {
  T <- params$T
  n_species <- length(N)
  dNdt <- numeric(n_species)  # Array to store derivatives
  
  for (i in 1:n_species) {
    competition_sum <- 0
    for (j in 1:n_species) {
      competition_sum <- competition_sum + predation_kernel(T, params$trait[i], params$trait[j], sigma) * N[j]
    }
    dNdt[i] <- N[i] * (params$r[i] - competition_sum)  # Growth equation
  }
  
  return(list(dNdt))
}

# Initial conditions
N_initial <- runif(n_species, 0.5, 1.5)  # Random initial population sizes

# Simulation parameters
time <- seq(0, 100, by = 0.1)

# Function to simulate and return the result
simulate_model <- function(T, N_initial, trait, r, time) {
  params <- list(T = T, trait = trait, r = r)
  ode(y = N_initial, times = time, func = limiting_similarity_model, parms = params)
}

# Simulate for baseline temperature
result_baseline <- simulate_model(T_baseline, N_initial, trait, r, time)

# Simulate for warming temperature
result_warming <- simulate_model(T_warming, N_initial, trait, r, time)

# Convert results to data frames for plotting
result_baseline_df <- as.data.frame(result_baseline)
result_warming_df <- as.data.frame(result_warming)

# Plot results for comparison between baseline and warming scenarios
plot_species_dynamics <- function(result_df, title) {
  result_melted <- reshape2::melt(result_df, id = "time")
  ggplot(result_melted, aes(x = time, y = value, color = variable)) +
    geom_line() +
    labs(title = title, x = "Time", y = "Population Size", color = "Species") +
    theme_minimal()
}

# Plot for baseline temperature
plot_species_dynamics(result_baseline_df, "Species Dynamics at Baseline Temperature")

# Plot for warming scenario
plot_species_dynamics(result_warming_df, "Species Dynamics under Warming Scenario")
