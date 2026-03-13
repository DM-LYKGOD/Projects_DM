library(deSolve)
library(ggplot2)


autocatalytic_cstr <- function(time, state, pars) {
  with(as.list(c(state, pars)), {
    dA <- dilution_rate * (A_in - A) - reaction_rate * A * B
    dB <- dilution_rate * (B_in - B) + reaction_rate * A * B
    dC <- -dilution_rate * C + reaction_rate * A * B
    list(c(dA, dB, dC))
  })
}


build_plot_frame <- function(simulation_df) {
  species <- c("A", "B", "C")
  data.frame(
    time = rep(simulation_df$time, times = length(species)),
    concentration = c(simulation_df$A, simulation_df$B, simulation_df$C),
    species = factor(rep(species, each = nrow(simulation_df)), levels = species)
  )
}


parameters <- list(
  dilution_rate = 0.25,
  reaction_rate = 1.20,
  A_in = 1.00,
  B_in = 0.05
)

initial_state <- c(
  A = 1.00,
  B = 0.05,
  C = 0.00
)

time_grid <- seq(0, 50, by = 0.1)
simulation <- as.data.frame(
  ode(y = initial_state, times = time_grid, func = autocatalytic_cstr, parms = parameters)
)

plot_df <- build_plot_frame(simulation)

ggplot(plot_df, aes(x = time, y = concentration, color = species)) +
  geom_line(linewidth = 0.9) +
  labs(
    title = "Autocatalytic Reaction in a Continuous Stirred-Tank Reactor",
    x = "Time",
    y = "Concentration"
  ) +
  theme_minimal()
