##Packages
library(ggplot2)
library(deSolve)

##Building our logistic Map Function
logistic_map <- function(x, r) {
  return(r * x * (1 - x))
}

## We set up a Function to identify periodic cycles in our logistic map
find_periodic_cycles <- function(r, num_iterations, tolerance = 1e-6) {
  x <- 0.5  # Initial value
  values <- numeric(num_iterations)
  values[1] <- x
  
## Iterating our logistic map
  for (i in 2:num_iterations) {
    x <- logistic_map(x, r)
    values[i] <- x
  }
  
## We Check for the periodic cycles by comparing the last few values
  cycle_length <- NA
  for (period in 1:(num_iterations / 2)) {
    if (all(abs(values[(num_iterations-period+1):num_iterations] - 
                values[(num_iterations-2*period+1):(num_iterations-period)]) < tolerance)) {
      cycle_length <- period
      break
    }
  }
  
  return(cycle_length)
}

## Generating data for bifurcation diagram and detecting the various periodic cycles
bifurcation_data <- function(r_min, r_max, num_r_values, num_iterations, last_iterations) {
  r_values <- seq(r_min, r_max, length.out = num_r_values)
  bifurcation_df <- data.frame(r = numeric(), x = numeric(), period = numeric())
  
  for (r in r_values) {
    x <- 0.5  # Initial population value
    x_values <- numeric(num_iterations)
    x_values[1] <- x
    
    # Iterating the logistic map once again, but in the growth rate loop
    for (i in 2:num_iterations) {
      x_values[i] <- logistic_map(x_values[i-1], r)
    }
    
    # Checking for periodic cycles in the last few iterations
    cycle_length <- find_periodic_cycles(r, num_iterations)
    
    # To capture stable cycles we only store the last few iterations 
    bifurcation_df <- rbind(bifurcation_df, 
                            data.frame(r = rep(r, last_iterations), 
                                       x = x_values[(num_iterations-last_iterations+1):num_iterations],
                                       period = rep(cycle_length, last_iterations)))
  }
  
  return(bifurcation_df)
}

## setting our Parameters for bifurcation diagram
r_min <- 2.5
r_max <- 4.0
num_r_values <- 1000
num_iterations <- 1000
last_iterations <- 100

## Setting up seed for reproducibility
set.seed(123)

## Now generating bifurcation data with the periodic cycle detection
bifurcation_df <- bifurcation_data(r_min, r_max, num_r_values, num_iterations, last_iterations)

## Exploring our logistic map function and plotting the bifurcation diagram with periodic cycles indicated using colors
ggplot(bifurcation_df, aes(x = r, y = x, color = as.factor(period))) +
  geom_point(size = 0.01, alpha = 0.3) +  # Points with different colors based on period
  scale_color_manual(values = c("1" = "blue", "2" = "green", "3"="yellow","4" = "red","8"= "orange"  ,"NA" = "navy")) +  
  labs(title = "Bifurcation Diagram Showing Periodic Cycles at Different Growth Rates", x = "Growth rate (r)", 
  y = "Population (x)", color = "Period") +
  theme_minimal() +
  theme(legend.position = "bottom")

##We also explored more to identify the chaotic regions where no periodicity occurs by 
##calculating the Lyapunov exponent for each growth rate r and 
##plotting them against the growth rates.
lyapunov_exponent <- function(r, num_iterations = 1000) {
  x <- 0.5  # Initial population value
  sum_lyapunov <- 0
  
  for (i in 1:num_iterations) {
    x <- logistic_map(x, r)
    lyap_step <- log(abs(r - 2 * r * x))  
    sum_lyapunov <- sum_lyapunov + lyap_step
  }
  
  return(sum_lyapunov / num_iterations)
}

## Finding Lyapunov exponents for the same r values
r_values <- seq(r_min, r_max, length.out = num_r_values)
lyapunov_values <- sapply(r_values, lyapunov_exponent)

## Plotting Lyapunov exponent vs Growth rate (r)
lyapunov_df <- data.frame(r = r_values, lyapunov = lyapunov_values)

ggplot(lyapunov_df, aes(x = r, y = lyapunov)) +
  geom_line(color = "blue") +
  geom_hline(yintercept = 0, linetype = "dashed", color = "black") +
  labs(title = "Lyapunov Exponent vs Growth Rate (r)", x = "Growth rate (r)", y = "Lyapunov Exponent") +
  theme_minimal()
##positive points indicate chaos or regions without periodicity

#Knowing the point where chaos started we analysed the transient behaviour
# Plotting both transient and final iterations for a selected growth rate
chosen_r <- 3.58  # We used a specific r value where chaos starts
x_values <- numeric(num_iterations)
x_values[1] <- 0.5  # Initial population

for (i in 2:num_iterations) {
  x_values[i] <- logistic_map(x_values[i - 1], chosen_r)
}

transient_df <- data.frame(iteration = 1:num_iterations, x = x_values)

ggplot(transient_df, aes(x = iteration, y = x)) +
  geom_line(color = "blue") +
  labs(title = paste("Transient and Long-Term Behavior for r =", chosen_r),
       x = "Iteration", y = "Population (x)") +
  theme_minimal()

