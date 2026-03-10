# Parameters
D_s <- 1  # Diffusion coefficient in cm^2 d^-1
O2_0 <- 300  # Initial oxygen concentration at the surface in mmol m^-3

# Define sediment depth (in cm)
depth <- seq(0, 5, by = 0.01)

# Function to calculate oxygen concentration profile
oxygen_profile <- function(k, D_s, O2_0, depth) {
  alpha <- sqrt(k / D_s)
  O2 <- O2_0 * exp(-alpha * depth)
  return(O2)
}

# Calculate oxygen profiles for different decay rates
O2_profile_k1 <- oxygen_profile(k = 1, D_s = D_s, O2_0 = O2_0, depth = depth)
O2_profile_k10 <- oxygen_profile(k = 10, D_s = D_s, O2_0 = O2_0, depth = depth)
O2_profile_k100 <- oxygen_profile(k = 100, D_s = D_s, O2_0 = O2_0, depth = depth)

# Plot the oxygen concentration profile for k = 10 d^-1
plot(depth, O2_profile_k10, type = "l", col = "blue", lwd = 2,
     xlab = "Sediment Depth (cm)", ylab = "Oxygen Concentration (mmol/m^3)",
     main = "Oxygen Concentration vs. Sediment Depth")

# Add profiles for k = 1 d^-1 and k = 100 d^-1
lines(depth, O2_profile_k1, col = "green", lwd = 2)
lines(depth, O2_profile_k100, col = "red", lwd = 2)

# Add a legend
legend("topright", legend = c("k = 1 d^-1", "k = 10 d^-1", "k = 100 d^-1", "Debapratim/Jonas"),
       col = c("green", "blue", "red","white"), lwd = 2)





#Calculation for step 3 " For each of these cases, calculate the flux of oxygen in the sediment and the oxygen penetration depth;"
# Parameters
D_s <- 1  # Diffusion coefficient in cm^2 d^-1
O2_0 <- 300  # Initial oxygen concentration at the surface in mmol m^-3

# Function to calculate flux
calculate_flux <- function(k, D_s, O2_0) {
  flux <- D_s * O2_0 * sqrt(k / D_s)
  return(flux)
}

# Function to calculate oxygen penetration depth
calculate_penetration_depth <- function(k, D_s, O2_0) {
  alpha <- sqrt(k / D_s)
  penetration_depth <- (1 / alpha) * log(O2_0 / 0.1)
  return(penetration_depth)
}

# Values of k to investigate
k_values <- c(1, 10, 100)

# Calculate flux and penetration depth for each k
results <- data.frame(
  k = k_values,
  Flux = sapply(k_values, calculate_flux, D_s = D_s, O2_0 = O2_0),
  Penetration_Depth = sapply(k_values, calculate_penetration_depth, D_s = D_s, O2_0 = O2_0)
)

# Print the results
print(results)

# Convert penetration depth to mm for the output
results$Penetration_Depth_mm <- results$Penetration_Depth * 10

# Display the final results
print(results)



#Step 4: "Make a graph of oxygen penetration depth in mm, versus oxygen flux, expressed in mmol m−2 d−1What is the relationship between both; can you explain?"
  
# Parameters
D_s <- 1  # Diffusion coefficient in cm^2 d^-1
O2_0 <- 300  # Initial oxygen concentration at the surface in mmol m^-3

# Function to calculate flux
calculate_flux <- function(k, D_s, O2_0) {
  flux <- D_s * O2_0 * sqrt(k / D_s)
  return(flux)
}

# Function to calculate oxygen penetration depth
calculate_penetration_depth <- function(k, D_s, O2_0) {
  alpha <- sqrt(k / D_s)
  penetration_depth <- (1 / alpha) * log(O2_0 / 0.1)
  return(penetration_depth)
}

# Values of k to investigate
k_values <- c(1, 10, 100)

# Calculate flux and penetration depth for each k
flux_values <- sapply(k_values, calculate_flux, D_s = D_s, O2_0 = O2_0)
penetration_depth_values <- sapply(k_values, calculate_penetration_depth, D_s = D_s, O2_0 = O2_0) * 10  # Convert to mm

# Create a plot of oxygen penetration depth vs. flux
plot(flux_values, penetration_depth_values, type = "b", pch = 16, col = "blue",
     xlab = "Oxygen Flux (mmol m^-2 d^-1)", ylab = "Oxygen Penetration Depth (mm)",
     main = "Oxygen Penetration Depth vs. Oxygen Flux\n Debapratim/Jonas")

# Add text labels for the decay rates (k values)
text(flux_values, penetration_depth_values, labels = paste("k =", k_values), pos = 4, cex = 0.8)





#Step 5: "Estimate the values of the parameters that can explain these observations.Which parameter would you vary in the first place? Use the fitting procedure from Section 4.4.2 to fit the model to the data."
# Install and load the minpack.lm package if not already installed
if (!require(minpack.lm)) {
  install.packages("minpack.lm")
}
library(minpack.lm)

# Observed data from the table
depth <- c(0, 0.1, 0.2, 0.3, 0.4, 0.5, 1.0)  # Sediment depth in cm
O2_concentration <- c(300, 65.52, 14.31, 3.13, 0.68, 0.59, 0.27)  # O2 concentration in mmol/m^3

# Fixed parameters
O2_0 <- 300  # Initial oxygen concentration at the surface
D_s_fixed <- 1  # Fixed diffusion coefficient in cm^2 d^-1

# Initial guess for decay rate
k_initial <- 50  # Initial guess for decay rate in d^-1

# Nonlinear least squares fitting using nlsLM (fitting only k)
fit <- nlsLM(O2_concentration ~ O2_0 * exp(-sqrt(k / D_s_fixed) * depth),
             start = list(k = k_initial),
             lower = c(0),  # Ensure k is positive
             control = list(maxiter = 1000))

# Summary of the fit
summary(fit)

# Extract fitted parameter
fitted_k <- coef(fit)['k']

# Print the fitted parameter
cat("Fitted decay rate (k):", fitted_k, "d^-1\n")
cat("Diffusion coefficient (D_s) was fixed at:", D_s_fixed, "cm^2 d^-1\n")

# Plot the observed data and fitted curve
plot(depth, O2_concentration, pch = 16, col = "blue",
     xlab = "Sediment Depth (cm)", ylab = "O2 Concentration (mmol/m^3)",
     main = "Observed Data and Fitted Oxygen Concentration Profile (Fitting k)\n Debapratim/Jonas")
curve(O2_0 * exp(-sqrt(fitted_k / D_s_fixed) * x), add = TRUE, col = "red", lwd = 2)

# Add a legend
legend("topright", legend = c("Observed Data", "Fitted Model"),
       col = c("blue", "red"), pch = c(16, NA), lwd = c(NA, 2))
