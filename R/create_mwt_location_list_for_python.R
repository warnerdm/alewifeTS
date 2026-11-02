library(tidyverse)
library(lubridate)
################################################################################
#now get trawl summary info for LM 
optroplist <- list.files("D:\\Acoustics\\EchoNet2Fish_LM\\",
                         pattern ="optrop", full.names = T,
                         recursive=T)
catchlist <- list.files("D:\\Acoustics\\EchoNet2Fish_LM\\",
                        pattern ="Acoustic_tr_catch", full.names = T,
                        recursive=T)
op_data <- read_csv(optroplist)%>%
  filter(LAKE==2 & !(OP_ID %in% c(106247, 106248))) # these two tows do not have required tow time information.
jub <- subset(op_data, OP_ID ==127578)
paste(jub$BEG_LATITUDE_DD, jub$BEG_LONGITUDE_DD)
opid <- op_data$OP_ID
catch_data <- read_csv(catchlist)%>%
  filter(OP_ID %in% opid & SPECIES %in% c(106,109,204))%>%
  select(-c(LIFE_STAGE, LF_N, WEIGHT))

# manual zero filling
all_combos <- expand.grid(SPECIES = c(106,109,204), OP_ID = unique(op_data$OP_ID))
filled_catch <- merge(all_combos, catch_data, by=c("OP_ID", "SPECIES"), all.x=TRUE)
filled_catch$N[is.na(filled_catch$N)]<-0
nprops <- filled_catch%>%
  group_by(OP_ID) %>%
  mutate(
    # Total catch for the specific tow
    total_tow_catch = sum(N),
    # Proportion of each species in that tow
    nprop = N / total_tow_catch
  ) %>%
  ungroup()%>%
  filter(total_tow_catch>0)
nprops$dom.spp <- NA
nprops$dom.spp[nprops$SPECIES==106 & nprops$nprop>=0.9]<- "Alewife"
nprops$dom.spp[nprops$SPECIES==109 & nprops$nprop>=0.9]<- "Smelt"
nprops$dom.spp[nprops$SPECIES==204 & nprops$nprop>=0.9]<- "Bloater"

alewife_tows <- subset(nprops, SPECIES==106 & nprop>=0.9 & N>=5)

mi_total_tows <- length(unique(op_data$OP_ID))


tows_species_dom <- subset(nprops, dom.spp %in% c("Alewife", "Smelt", "Bloater"))
jub <- subset(tows_species_dom, dom.spp=="Alewife")
jub1 <- subset(tows_species_dom, dom.spp=="Smelt")

#we need to have op fields for use in python
opfields <- op_data%>%
  filter(OP_ID %in% alewife_tows$OP_ID)%>%
  select(c("OP_ID", "LAKE", "YEAR","VESSEL", "OP_DATE",  "TIME",  "TRANSECT",  "TOW_TIME",
           "FISHING_DEPTH",   "BEG_LATITUDE_DD",           
           "BEG_LONGITUDE_DD",   "END_LATITUDE_DD",  "END_LONGITUDE_DD",
           "BEG_DEPTH", "END_DEPTH",  
           "FISHING_TEMP")   )%>%
  mutate(trawl_ht = 10, TR_DESIGN=NA, MESH_SIZE=NA, SPEED=NA, SURF_TEMP=NA)

tow_list <- merge(opfields, alewife_tows, by = "OP_ID")%>%
  filter(N>=3)
tow_list$OP_DATE
tow_list$TIME

time_str <- sprintf("%04d", tow_list$TIME)              # "227" -> "0227", "45" -> "0045", "0" -> "0000"
time_parsed <- parse_date_time(time_str, orders = "HM")

op_date_parsed <- parse_date_time(tow_list$OP_DATE, orders = c("mdY HM", "Ymd HMS", "Ymd", "mdY"))
date_only <- as.Date(op_date_parsed)

datetime <- as.POSIXct(paste(date_only, format(time_parsed, "%H:%M:%S")))
datetime_str <- format(datetime, "%Y-%m-%dT%H:%M:%S")
tow_list$datetime <- format(datetime, "%Y-%m-%dT%H:%M:%S")
tow_list$acoustic_format <-NA
tow_list$acoustic_format[tow_list$VESSEL==35] <- "raw" 
tow_list$acoustic_format[tow_list$VESSEL==88 & tow_list$YEAR >2021]<- "raw"
tow_list$acoustic_format[tow_list$VESSEL==17] <- "dt4"
tow_list$acoustic_format[tow_list$VESSEL==88 & tow_list$YEAR <2022]<- "dt4"
tow_list$acoustic_format[tow_list$VESSEL==37] <- "raw" 
tow_list$datetime[tow_list$OP_ID == 89428] <- "2014-08-08T02:29:00" #These two tows were given the wrong date
tow_list$datetime[tow_list$OP_ID == 93075] <- "2015-08-15T02:10:00"

final_list <- tow_list%>%
  select(-c(dom.spp, N, nprop,SPECIES, total_tow_catch))%>%
  mutate(fishing_depth_source ="sensor(Simrad/Netmind/Marport)")


write.csv(final_list, "D:/pyprojects/alewifeTS/data/raw/LM_tow_list_2005_2024.csv", row.names = FALSE)



###############################################################################################
# This section repeats the above but for any tow that had one of the three species >=90%
# of the catch and writes it. 
#we need to have op fields for use in python
opfields <- data.frame(OP_ID = op_data$OP_ID, OP_DATE = op_data$OP_DATE, 
                       VESSEL = op_data$VESSEL, TRANSECT = op_data$TRANSECT, TIME = op_data$TIME, YEAR = op_data$YEAR, 
                       TOW_TIME = op_data$TOW_TIME, FISHING_DEPTH = op_data$FISHING_DEPTH, 
                       trawl_ht = 10)

tow_list <- merge(opfields, tows_species_dom, by = "OP_ID")%>%
  filter(N>=3)
tow_list$datetime_obj <- parse_date_time(tow_list$OP_DATE, orders = c("mdY HM", "Ymd HMS", "Ymd"))
tow_list$datetime_obj[is.na(tow_list$datetime_obj)]<- parse_date_time(tow_list$OP_DATE, orders = c("mdY HM", "Ymd HMS", "Ymd", "mdY"))
tow_list$TIME


time_str <- sprintf("%04d", tow_list$TIME)              # "227" -> "0227", "45" -> "0045", "0" -> "0000"
time_parsed <- parse_date_time(time_str, orders = "HM")

op_date_parsed <- parse_date_time(tow_list$OP_DATE, orders = c("mdY HM", "Ymd HMS", "Ymd", "mdY"))
date_only <- as.Date(op_date_parsed)

datetime <- as.POSIXct(paste(date_only, format(time_parsed, "%H:%M:%S")))
datetime_str <- format(datetime, "%Y-%m-%dT%H:%M:%S")
tow_list$datetime <- format(datetime, "%Y-%m-%dT%H:%M:%S")
tow_list$acoustic_format <-NA
tow_list$acoustic_format[tow_list$VESSEL==35] <- "raw" 
tow_list$acoustic_format[tow_list$VESSEL==88 & tow_list$YEAR >2021]<- "raw"
tow_list$acoustic_format[tow_list$VESSEL==17] <- "dt4"
tow_list$acoustic_format[tow_list$VESSEL==88 & tow_list$YEAR <2022]<- "dt4"
tow_list$acoustic_format[tow_list$VESSEL==37] <- "raw" 

final_list <- tow_list%>%
  select(OP_ID, VESSEL, TRANSECT, TOW_TIME, FISHING_DEPTH, trawl_ht,datetime, acoustic_format,
         dom.spp)
#write.csv(final_list, "./data/LM_tow_list_for_python_multispecies.csv", row.names = FALSE)












