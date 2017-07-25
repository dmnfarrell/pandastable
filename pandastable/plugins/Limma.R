#pairwise DE analysis with limma

args<-commandArgs(TRUE)
library(edgeR)
data <- as.matrix(read.csv(args[1],row.names=1))
data[is.na(data)] <- 0
#head(data,5)
#lirary size for normalisation
libSizes <- as.vector(colSums(data))
#libSizes
#extract groups from colnames
split <- (strsplit(colnames(data), "_"))
g <- (sapply(split,"[", 2))

dge <- DGEList(counts=data,group=g,lib.size=libSizes)
y <- calcNormFactors(dge)

#limma-trend
group <- factor(c(g))
print (group)
design <- model.matrix(~ 0+group)
#colnames (design) <- gsub ("group", "", colnames (design))
#print (design)
v <- voom(y,design)

#print (design)
logcounts <- cpm(y,log=TRUE)
head(logcounts, 5)

fit <- lmFit(logcounts, design)
#fit <- eBayes(fit, trend=TRUE)
#results <- topTable(fit, coef=ncol(design))

cont.matrix <- makeContrasts('group1-group0',levels=design)
fit.cont <- contrasts.fit(fit, cont.matrix)
fit.cont <- eBayes(fit.cont)
summa.fit <- decideTests(fit.cont)
results <- topTable(fit.cont,coef=1, n=dim (v$E)[1])
results <- results[order (results$adj.P.Val), ]
#head (results,n=10)

res <- data.frame(results)
#print (res)
write.csv(res, "limma_output.csv")
#png(filename='limma_md.png', width = 1000, height = 1000, units='px', res=150)
#plotMD(fit.cont,coef=1,status=summa.fit[,])
