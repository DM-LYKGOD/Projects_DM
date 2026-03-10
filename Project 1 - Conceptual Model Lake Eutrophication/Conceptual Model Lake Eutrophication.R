
windows (width= 20, height= 10)

# Load necessary libraries
library(deSolve)
library(ggplot2)

# Define the parameters for different scenarios
params_scenario1 <- list(
  r_P = 1.0,    # Phytoplankton growth rate
  K_P = 0.5,    # Half-saturation constant for phosphorus
  g_Z = 0.3,    # Zooplankton grazing rate
  p_F = 0.4,    # Fish predation rate on zooplankton
  r_F = 0.05,   # Fish growth rate
  m_F = 0.1,    # Biomanipulation (fishing) rate (Scenario 1: Low fishing rate)
  I_P = 1.0,    # Phosphorus input rate (Scenario 1: Moderate phosphorus)
  u_P = 0.2     # Phytoplankton uptake rate of phosphorus
)

params_scenario2 <- list(
  r_P = 1.0,    
  K_P = 0.5,    
  g_Z = 0.3,    
  p_F = 0.4,    
  r_F = 0.05,   
  m_F = 0.3,    # Biomanipulation (fishing) rate (Scenario 2: High fishing rate)
  I_P = 1.5,    # Phosphorus input rate (Scenario 2: High phosphorus)
  u_P = 0.2     
)

params_scenario3 <- list(
  r_P = 1.0,    
  K_P = 0.5,    
  g_Z = 0.3,    
  p_F = 0.4,    
  r_F = 0.05,   
  m_F = 0.05,   # Biomanipulation (fishing) rate (Scenario 3: Very low fishing rate)
  I_P = 0.7,    # Phosphorus input rate (Scenario 3: Low phosphorus)
  u_P = 0.2     
)

# Define initial conditions
initial_state <- c(
  P = 0.5,  # Phytoplankton biomass
  Z = 0.3,  # Zooplankton biomass
  F = 0.2,  # Fish population
  C = 0.8   # Phosphorus concentration
)

# Define the time sequence for the simulation
time_seq <- seq(0, 200, by = 1)

# Define the system of differential equations
lake_model <- function(time, state, parameters) {
  with(as.list(c(state, parameters)), {
    
    # Phytoplankton dynamics
    dP <- r_P * P * (C / (C + K_P)) - g_Z * Z * P
    
    # Zooplankton dynamics
    dZ <- g_Z * Z * P - p_F * F * Z
    
    # Fish dynamics
    dF <- r_F * F - m_F * F
    
    # Phosphorus dynamics
    dC <- I_P - u_P * P
    
    # Return the rate of changes
    return(list(c(dP, dZ, dF, dC)))
  })
}

# Run the simulation for all three scenarios
output_scenario1 <- ode(y = initial_state, times = time_seq, func = lake_model, parms = params_scenario1)
output_scenario2 <- ode(y = initial_state, times = time_seq, func = lake_model, parms = params_scenario2)
output_scenario3 <- ode(y = initial_state, times = time_seq, func = lake_model, parms = params_scenario3)

# Convert outputs to data frames
output_df1 <- as.data.frame(output_scenario1)
output_df1$Scenario <- "Scenario 1 (Low fishing, Moderate P)"

output_df2 <- as.data.frame(output_scenario2)
output_df2$Scenario <- "Scenario 2 (High fishing, High P)"

output_df3 <- as.data.frame(output_scenario3)
output_df3$Scenario <- "Scenario 3 (Very low fishing, Low P)"

# Combine all data frames into one for comparison
output_combined <- rbind(output_df1, output_df2, output_df3)

# Plot the results using ggplot2
ggplot(output_combined, aes(x = time)) +
  geom_line(aes(y = P, color = "Phytoplankton")) +
  geom_line(aes(y = Z, color = "Zooplankton")) +
  geom_line(aes(y = F, color = "Fish")) +
  geom_line(aes(y = C, color = "Phosphorus")) +
  facet_wrap(~Scenario) +
  labs(
    title = "Effect of Biomanipulation on Lake Ecosystem Across Scenarios\n(Debapratim/Jonas)",
    x = "Time",
    y = "Biomass/Concentration",
    color = "Components"
  ) +
  theme_minimal() +
  theme(plot.title = element_text(hjust = 0.5)) # Center the title
