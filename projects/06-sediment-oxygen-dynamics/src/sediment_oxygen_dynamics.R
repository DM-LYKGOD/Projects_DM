oxygen_profile <- function(k, diffusion, surface_oxygen, depth) {
  alpha <- sqrt(k / diffusion)
  surface_oxygen * exp(-alpha * depth)
}


calculate_flux <- function(k, diffusion, surface_oxygen) {
  diffusion * surface_oxygen * sqrt(k / diffusion)
}


calculate_penetration_depth <- function(k, diffusion, surface_oxygen, cutoff = 0.1) {
  alpha <- sqrt(k / diffusion)
  (1 / alpha) * log(surface_oxygen / cutoff)
}


summarize_cases <- function(k_values, diffusion, surface_oxygen, depth) {
  profiles <- lapply(k_values, function(k) {
    oxygen_profile(k = k, diffusion = diffusion, surface_oxygen = surface_oxygen, depth = depth)
  })

  summary_df <- data.frame(
    k = k_values,
    flux = sapply(k_values, calculate_flux, diffusion = diffusion, surface_oxygen = surface_oxygen),
    penetration_depth_cm = sapply(
      k_values,
      calculate_penetration_depth,
      diffusion = diffusion,
      surface_oxygen = surface_oxygen
    )
  )
  summary_df$penetration_depth_mm <- summary_df$penetration_depth_cm * 10

  profile_df <- do.call(
    rbind,
    lapply(seq_along(k_values), function(index) {
      data.frame(
        depth = depth,
        oxygen = profiles[[index]],
        scenario = paste("k =", k_values[index], "d^-1")
      )
    })
  )

  list(summary = summary_df, profiles = profile_df)
}


plot_profiles <- function(profile_df) {
  plot(
    oxygen ~ depth,
    data = subset(profile_df, scenario == unique(profile_df$scenario)[1]),
    type = "l",
    col = "forestgreen",
    lwd = 2,
    xlab = "Sediment Depth (cm)",
    ylab = "Oxygen Concentration (mmol/m^3)",
    main = "Oxygen Concentration vs. Sediment Depth"
  )

  colors <- c("forestgreen", "steelblue", "firebrick")
  scenarios <- unique(profile_df$scenario)
  for (index in seq_along(scenarios)) {
    lines(
      oxygen ~ depth,
      data = subset(profile_df, scenario == scenarios[index]),
      col = colors[index],
      lwd = 2
    )
  }

  legend("topright", legend = scenarios, col = colors, lwd = 2)
}


plot_flux_vs_depth <- function(summary_df) {
  plot(
    summary_df$flux,
    summary_df$penetration_depth_mm,
    type = "b",
    pch = 16,
    col = "steelblue",
    xlab = "Oxygen Flux (mmol m^-2 d^-1)",
    ylab = "Oxygen Penetration Depth (mm)",
    main = "Oxygen Penetration Depth vs. Oxygen Flux"
  )
  text(
    summary_df$flux,
    summary_df$penetration_depth_mm,
    labels = paste("k =", summary_df$k),
    pos = 4,
    cex = 0.8
  )
}


fit_decay_rate <- function(depth_obs, oxygen_obs, diffusion, surface_oxygen) {
  if (!requireNamespace("minpack.lm", quietly = TRUE)) {
    stop("Package 'minpack.lm' is required to fit the decay rate.")
  }

  minpack.lm::nlsLM(
    oxygen_obs ~ surface_oxygen * exp(-sqrt(k / diffusion) * depth_obs),
    start = list(k = 50),
    lower = c(0),
    control = minpack.lm::nls.lm.control(maxiter = 1000)
  )
}


plot_fitted_profile <- function(depth_obs, oxygen_obs, fitted_k, diffusion, surface_oxygen) {
  plot(
    depth_obs,
    oxygen_obs,
    pch = 16,
    col = "steelblue",
    xlab = "Sediment Depth (cm)",
    ylab = "Oxygen Concentration (mmol/m^3)",
    main = "Observed Data and Fitted Oxygen Concentration Profile"
  )
  curve(
    surface_oxygen * exp(-sqrt(fitted_k / diffusion) * x),
    add = TRUE,
    col = "firebrick",
    lwd = 2
  )
  legend(
    "topright",
    legend = c("Observed Data", "Fitted Model"),
    col = c("steelblue", "firebrick"),
    pch = c(16, NA),
    lwd = c(NA, 2)
  )
}


diffusion <- 1
surface_oxygen <- 300
depth_grid <- seq(0, 5, by = 0.01)
k_values <- c(1, 10, 100)

results <- summarize_cases(
  k_values = k_values,
  diffusion = diffusion,
  surface_oxygen = surface_oxygen,
  depth = depth_grid
)

print(results$summary)
plot_profiles(results$profiles)
plot_flux_vs_depth(results$summary)

depth_obs <- c(0, 0.1, 0.2, 0.3, 0.4, 0.5, 1.0)
oxygen_obs <- c(300, 65.52, 14.31, 3.13, 0.68, 0.59, 0.27)
fit <- fit_decay_rate(
  depth_obs = depth_obs,
  oxygen_obs = oxygen_obs,
  diffusion = diffusion,
  surface_oxygen = surface_oxygen
)

fitted_k <- coef(fit)[["k"]]
cat("Fitted decay rate (k):", fitted_k, "d^-1\n")
cat("Diffusion coefficient (D_s):", diffusion, "cm^2 d^-1\n")
plot_fitted_profile(
  depth_obs = depth_obs,
  oxygen_obs = oxygen_obs,
  fitted_k = fitted_k,
  diffusion = diffusion,
  surface_oxygen = surface_oxygen
)
