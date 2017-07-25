#pairwise DE analysis with edgeR

args<-commandArgs(TRUE)
library(edgeR)
#library(gplots)

data <- as.matrix(read.csv(args[1],row.names=1))
data[is.na(data)] <- 0
#head(data,5)
#lirary size for normalisation
libSizes <- as.vector(colSums(data))
#libSizes
#extract groups from colnames
split <- (strsplit(colnames(data), "_"))
g <- (sapply(split,"[", 2))

#g<-colnames(data)
#g
#plotMDS( data , main = "MDS Plot for Count Data")

dge <- DGEList(counts=data,group=g,lib.size=libSizes)
#deDGE(d, doPoisson=True)
y <- calcNormFactors(dge)

#edgeR
d <- estimateCommonDisp(y)
d <- estimateTagwiseDisp(d)
de.com <- exactTest(d)
results <- topTags(de.com,n = length(data[,1]))
#results
res <- data.frame(results)
#res <- subset(res, (res$PValue < 0.01) & (res$logFC>1.5 | res$logFC< -1.5))
res <- res[order(-res$logFC),]
#res
write.csv(res, "edger_output.csv")
#png(filename='smear.png')
#plotSmear(d , de.tags=de.com)
#abline(v=c(-2, 2), col=2)
