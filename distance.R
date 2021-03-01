if (!require('devtools')) install.packages('devtools')
if (!require('parallel')) install.packages('parallel')
if (!require('maps')) devtools::install_github('adeckmyn/maps') #the newest version possible
if (!require('geosphere')) install.packages('geosphere')
if (!require('data.table')) install.packages('data.table')

fast.merge.df<-function(DF1, DF2, by, all.x =TRUE, all.y=TRUE){
  DT1 <- data.table::data.table(DF1, key=by)
  DT2 <- data.table::data.table(DF2, key=by)
  data.frame(data.table:::merge.data.table(DT1, DT2, all.x=all.x, all.y=all.y),
             stringsAsFactors = FALSE)
}

getDistance<-function(long1,lat1,long2,lat2) 
  sapply(seq_along(long1), 
         function(k) geosphere::distGeo(
           c(long1[k],lat1[k]),
           c(long2[k],lat2[k])))

get_avg_distance<-function(Origin, 
                           Dest, 
                           cities,
                           maxcit=25){
  
  citiesO<-cities[cities$country.etc==Origin,]
  NO<-min(nrow(citiesO),maxcit)
  citiesO<-citiesO[order(citiesO$pop,decreasing = TRUE),][seq_len(NO),]
  
  citiesD<-cities[cities$country.etc==Dest,]
  ND<-min(nrow(citiesD),maxcit)
  citiesD<-citiesD[order(citiesD$pop,decreasing = TRUE),][seq_len(ND),]
  
  bc_distance<-getDistance(citiesD$long[1],citiesD$lat[1],
                           citiesO$long[1],citiesO$lat[1])/1000
  
  citiesD$name<-paste(citiesD$name,seq_along(citiesD$name),sep='_')
  citiesO$name<-paste(citiesO$name,seq_along(citiesO$name),sep='_')
  tmp<-expand.grid(CO=citiesO$name,CD=citiesD$name,stringsAsFactors = FALSE)
  CitD<-fast.merge.df(tmp, data.frame(CD=citiesD$name,
                                      popD=citiesD$pop,
                                      latD=citiesD$lat,
                                      longD=citiesD$long,
                                      stringsAsFactors = FALSE),by='CD')
  CitO<-fast.merge.df(tmp, data.frame(CO=citiesO$name,
                                      popO=citiesO$pop,
                                      latO=citiesO$lat,
                                      longO=citiesO$long,
                                      stringsAsFactors = FALSE),by='CO')
  CitD$ind<-paste(CitD$CO,CitD$CD,sep='_x_')
  CitO$ind<-paste(CitO$CO,CitO$CD,sep='_x_')
  CitD<-CitD[order(CitD$ind),]
  CitO<-CitO[order(CitO$ind),]
  if (!all(CitD$ind==CitO$ind)) stop()
  distance<-getDistance(CitD$long,CitD$lat,
                        CitO$long,CitO$lat)/1000
  H<-max(CitO$popO,CitD$popD)
  CitO$popO<-CitO$popO/H
  CitD$popD<-CitD$popD/H
  
  sum_wO<-sum(CitO$popO[!duplicated(CitO$CO)])
  sum_wD<-sum(CitD$popD[!duplicated(CitD$CD)])
  WO_WD_dist<-CitO$popO*CitD$popD*distance
  list(Origin=Origin,
       Dest=Dest,
       Origin.NC=NO,
       Dest.NC=ND,
       pop_weighted=sum(WO_WD_dist)/(sum_wD*sum_wO), 
       average=mean(distance),
       biggest_cit=bc_distance)
}

cities <- maps::world.cities
countries<-unique(cities$country.etc)
CntrList<-expand.grid(Origin=countries,Dest=countries)
CntrList<-CntrList[CntrList$Origin!=CntrList$Dest,]

#Number of the biggest cities
nCit<-50

# example 
get_avg_distance('Norway', 'Sweden', cities, nCit)$pop_weighted

# all cases, can take long time depending on nCit
numCores <- max(1, detectCores() - 1)
DIST<-parallel::mclapply(seq_along(CntrList$Origin),
                         function(k) {
                           get_avg_distance(CntrList$Origin[k], CntrList$Dest[k], cities=cities, maxcit = nCit)
                         },  mc.cores = numCores); 
DIST<-data.table::rbindlist(DIST)
save(list='DIST',file="geo_distances.rda")