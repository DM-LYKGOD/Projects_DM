r= 0.1
K= 10
windows (width= 10, height= 10)
curve (expr= r*x*(1-x/K),from=0,to=20,lwd=2,
       xlab="density, N",ylab="rate of change, dN/dt")
legend ("topright",c("K=10","r=0.1", "Debapratim/ Jonas"))