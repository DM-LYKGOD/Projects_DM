autocatalysis <- function(t,state,pars) {
  with (as.list(c(state,pars)),
        {
          dA <- dr*(Ain-A)-k*A*B
          dB <- dr*(Bin-B)+k*A*B
          dC <--dr*C+k*A*B
          return (list(c(dA,dB,dC)))
        })
}