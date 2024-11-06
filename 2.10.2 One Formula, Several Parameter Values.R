windows(width= 10, height= 10)
food <- seq(0,30,by=0.1)
ks <- seq (1,10, by=2)
foodmat <- outer(food,ks,function(x,y) x /(y +x))

matplot(x=food, foodmat, type="l", col="black",
        xlab="food", ylab="-", lwd=2,
        main= expression (frac(food ,food+ks)))

legend("bottomright", as.character(ks), title="ks=",
       lty=1:5, lwd=2)

# Adjust margins to make room for label
par(xpd=TRUE, mar=c(5, 4, 4, 7))  # Increase the right margin

# Add label outside the plot, in the bottom-right corner
mtext("Debapratim/ Jonas", side=1, line=4, col="black", cex=1)
