library(deSolve)
library(ggplot2)


build_scenarios <- function() {
  list(
    "Scenario 1 (Low fishing, Moderate P)" = list(
      r_P = 1.0,
      K_P = 0.5,
      g_Z = 0.3,
      p_F = 0.4,
      r_F = 0.05,
      m_F = 0.1,
      I_P = 1.0,
      u_P = 0.2
    ),
    "Scenario 2 (High fishing, High P)" = list(
      r_P = 1.0,
      K_P = 0.5,
      g_Z = 0.3,
      p_F = 0.4,
      r_F = 0.05,
      m_F = 0.3,
      I_P = 1.5,
      u_P = 0.2
    ),
    "Scenario 3 (Very low fishing, Low P)" = list(
      r_P = 1.0,
      K_P = 0.5,
      g_Z = 0.3,
      p_F = 0.4,
      r_F = 0.05,
      m_F = 0.05,
      I_P = 0.7,
      u_P = 0.2
    )
  )
}


lake_model <- function(time, state, parameters) {
  with(as.list(c(state, parameters)), {
    dP <- r_P * P * (C / (C + K_P)) - g_Z * Z * P
    dZ <- g_Z * Z * P - p_F * F * Z
    dF <- r_F * F - m_F * F
    dC <- I_P - u_P * P
    list(c(dP, dZ, dF, dC))
  })
}


simulate_lake_scenarios <- function(initial_state, time_grid, scenarios) {
  scenario_outputs <- lapply(names(scenarios), function(label) {
    output <- as.data.frame(
      ode(y = initial_state, times = time_grid, func = lake_model, parms = scenarios[[label]])
    )
    output$Scenario <- label
    output
  })
  do.call(rbind, scenario_outputs)
}


plot_lake_dynamics <- function(simulation_df) {
  ggplot(simulation_df, aes(x = time)) +
    geom_line(aes(y = P, color = "Phytoplankton")) +
    geom_line(aes(y = Z, color = "Zooplankton")) +
    geom_line(aes(y = F, color = "Fish")) +
    geom_line(aes(y = C, color = "Phosphorus")) +
    facet_wrap(~Scenario) +
    labs(
      title = "Lake eutrophication dynamics across nutrient and fishing scenarios",
      x = "Time",
      y = "Biomass / Concentration",
      color = "Component"
    ) +
    theme_minimal()
}


build_logistic_reference <- function(r = 0.1, carrying_capacity = 10, density_max = 20, step = 0.1) {
  density <- seq(0, density_max, by = step)
  data.frame(
    density = density,
    growth_rate = r * density * (1 - density / carrying_capacity)
  )
}


plot_logistic_reference <- function(reference_df, r, carrying_capacity) {
  ggplot(reference_df, aes(x = density, y = growth_rate)) +
    geom_line(linewidth = 1) +
    labs(
      title = "Logistic growth reference for phytoplankton density",
      subtitle = paste("r =", r, "| carrying capacity =", carrying_capacity),
      x = "Density",
      y = "dN/dt"
    ) +
    theme_minimal()
}


build_uptake_sensitivity <- function(food_max = 30, food_step = 0.1, half_saturation_values = seq(1, 10, by = 2)) {
  food <- seq(0, food_max, by = food_step)
  grid <- expand.grid(food = food, K = half_saturation_values)
  grid$uptake_fraction <- grid$food / (grid$K + grid$food)
  grid
}


plot_uptake_sensitivity <- function(sensitivity_df) {
  ggplot(sensitivity_df, aes(x = food, y = uptake_fraction, color = factor(K))) +
    geom_line(linewidth = 1) +
    labs(
      title = "Nutrient uptake sensitivity across half-saturation constants",
      x = "Available nutrient / food",
      y = "food / (food + K)",
      color = "K"
    ) +
    theme_minimal()
}


main <- function() {
  scenarios <- build_scenarios()
  initial_state <- c(P = 0.5, Z = 0.3, F = 0.2, C = 0.8)
  time_grid <- seq(0, 200, by = 1)

  simulation_df <- simulate_lake_scenarios(
    initial_state = initial_state,
    time_grid = time_grid,
    scenarios = scenarios
  )
  logistic_reference_df <- build_logistic_reference()
  uptake_sensitivity_df <- build_uptake_sensitivity()

  print(plot_lake_dynamics(simulation_df))
  print(plot_logistic_reference(logistic_reference_df, r = 0.1, carrying_capacity = 10))
  print(plot_uptake_sensitivity(uptake_sensitivity_df))
}


main()
