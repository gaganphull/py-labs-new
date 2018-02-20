#functions
import numpy as np
import cv2
import matplotlib.pyplot as plt
import math
import copy
import itertools as it
import csv
import PIL.Image
import PIL.ExifTags
import pandas as pd
import statsmodels.discrete.discrete_model as sm
import statsmodels.tools.tools as sm_tool
from operator import itemgetter
from sklearn.linear_model import LogisticRegression
from sklearn.linear_model import LogisticRegressionCV
from sklearn.svm import LinearSVC
from sklearn.cross_validation import train_test_split
from sklearn import metrics

#converts nan to binary where nan values are 0 and non-nan values are 1
def nanTObin(input_mat,flipper=False):
    output_mat = np.ones(input_mat.shape)
    if not flipper:
        for i in np.arange(input_mat.shape[0]):
            for j in np.arange(input_mat.shape[1]):
                if np.isnan(input_mat[i,j]):
                    output_mat[i,j] = 0
    else:
        output_mat[:] = np.nan
        for i in np.arange(input_mat.shape[0]):
            for j in np.arange(input_mat.shape[1]):
                if not input_mat[i,j] == 0:
                    output_mat[i,j] = 0
    return output_mat

#makes a radially symmetrical gaussian filter based on input image dimentions
def gauss_maker(fig_rows,fig_cols,sigma_perc,anchor_perc_rows,anchor_perc_cols,max_val=1,flipper=False):
    #initialize sigma and k
    sigma = np.sqrt(fig_rows ** 2 + fig_cols ** 2) * sigma_perc
    
    k = int(max([fig_rows,fig_cols])) * 2
    sigma_fix = 0.3 * ((k - 1) * 0.5 - 1) + 0.8
    print str(sigma) + ',' + str(sigma_fix)
    #Calculate kernel
    kernel_1d = cv2.getGaussianKernel(k,sigma)
    kernel_1d = kernel_1d / max(kernel_1d) * max_val
    filler_fig = np.ones([fig_rows,fig_cols])

    anchor_rows = int(fig_rows * anchor_perc_rows)
    anchor_cols = int(fig_cols * anchor_perc_cols)

    for j in np.arange(fig_cols):
        for i in np.arange(fig_rows):
            anchor_diff_row = i - anchor_rows
            anchor_diff_col = j - anchor_cols
            kernel_loc_row = int(np.ceil(k / float(2)) + anchor_diff_row)
            kernel_loc_col = int(np.ceil(k / float(2)) + anchor_diff_col)
            # print kernel_loc
            filler_fig[i,j] = filler_fig[i,j] * kernel_1d[kernel_loc_row] * kernel_1d[kernel_loc_col]
    if flipper:
        final_fig = -(filler_fig - max_val)
        filler_fig = final_fig
    return filler_fig

#automatically makes subplots from a list of mats
def plotter(input_list):
    numberOFplots = len(input_list)
    for i in np.arange(numberOFplots):
        plt.subplot(1,numberOFplots,i + 1)
        plt.imshow(input_list[i])
    plt.show()
    return

#converts from bgr to cct
def cct(input_img):
    i_ext = cv2.cvtColor(input_img,cv2.COLOR_BGR2XYZ)
    #plt.imshow(i_ext)
    #plt.show()
    i_cct = np.zeros_like(i_ext[:,:,0],float)
    #i_cct.astype(float)
    for i in range(0,i_ext.shape[0]):
        for j in range(0,i_ext.shape[1]):
            X = float(i_ext[i,j,0])
            Y = float(i_ext[i,j,1])
            Z = float(i_ext[i,j,2])
            #print X
            #print Y
            #print Z
            breaker=False
            if not (X+Y+Z)==0:
                x = (X) / (X + Y + Z);
                y = (Y) / (X + Y + Z);
            else:
                breaker=True
            if not breaker:
                if not (0.1858 - y)==0:
                    n = (x - 0.3320) / (0.1858 - y);
                else:
                    breaker=True
           # print n
            if not breaker: 
                CCT = 449.0*pow(n, 3) + 3525.0*pow(n, 2) + 6823.3*n + 5520.33;
            #print CCT
            if CCT<20000 and CCT>0 and not breaker:
                i_cct[i,j] = CCT
    print type(i_cct[0,0])
    print i_cct
    return i_cct


def area_filter(input_img,min_area,max_area=0):
    contours, hierarchy = cv2.findContours(copy.copy(input_img), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    print len(contours)
    contour_filter=[]
    for cnt in contours:
        area=cv2.contourArea(cnt)
        #if not min_area==0:
        #    if area>min_area and area<max_area:
        #        contour_filter.append(cnt)
        if True:
            if area>min_area:
                contour_filter.append(cnt)
                #print 'append'
    print len(contour_filter)
    img_black=np.zeros_like(input_img)
    plt.imshow(img_black)
    plt.show()
    cv2.drawContours(img_black,contour_filter,-1,(255))
    plt.imshow(img_black)
    plt.show()
    
    return img_black

def multi_photo_model(csv_file,photo_number,test_type,unique_array,mark,confidence,mark_pred, printer=False):
     #count rows
    with open(csv_file) as csvfile:
        readCSV = csv.reader(csvfile,delimiter=',')
        row_count = sum(1 for row in readCSV)

    with open(csv_file) as csvfile:
        readCSV = csv.reader(csvfile,delimiter=',')
        for row in readCSV:
            col_count = len(row)
            break

    #Import Data
    if printer:
        print 'Import Data...'
    all_data = np.zeros(shape=(row_count - 1,col_count))
    row_count = 0
    with open(csv_file) as csvfile:
        readCSV = csv.reader(csvfile,delimiter=',')
        counter = 0
        for row in readCSV:
            if counter > 0:
                try:
                    all_data[row_count,:] = row
                    row_count+=1
                except:
                    if printer:
                        print "Row Import Failed"
            else:
                headers = row
            counter+=1
    if printer:
        print all_data

    unique_vals = []
    for i in unique_array:
        unique_list = np.unique(all_data[:,i])
        unique_vals.append(unique_list)

    if printer:
        print unique_vals

    #Construct vector of unique values, saved as strings
    if printer:
        print 'Construct vector of unique values, saved as strings...'
    unique_vals_string = []
    for i in np.arange(len(unique_vals)):
        unique_vals_string.append([])
        for j in np.arange(len(unique_vals[i])):
            unique_vals_string[i].append(str(unique_vals[i][j]))

    #construct super vector with all possible combinations of unique vals
    if printer:
        print 'construct super vector with all possible combinations of unique vals...'
        print unique_vals_string
    super_list = [" ".join(i) for i in it.product(*unique_vals_string)]

    #for items in it.product(*unique_vals_string):
    #    super_list.append(items)
    
    if printer:
        print super_list

    #construct holding dictionary
    if printer:
        print 'construct holding dictionary...'
    values_dictionary = {}
    for i in np.arange(len(super_list)):
        values_dictionary[super_list[i]] = [[],[],[]]
    if printer:
        print values_dictionary.keys()
    #add data to holding dictionary
    if printer:
        print 'add data to holding dictionary...'
    for row in np.arange(row_count):
        key = ''
        for val in unique_array:
            key+=str(all_data[row,val]) + ' '
            
        key = key[:-1]
        #print key
        values_dictionary[key][0].append(all_data[row,mark])
        values_dictionary[key][1].append(all_data[row,confidence])
        values_dictionary[key][2].append(all_data[row,mark_pred])

    #plot data
    if printer:
        print 'model data...'
    TP=0;
    FP=0;
    TN=0;
    FN=0;
    super_counter=0
    for i in super_list:
        mark_data=values_dictionary[i][0]
        confidence_data=values_dictionary[i][1]
        mark_pred_data=values_dictionary[i][2]
        data_set_size=len(confidence_data)
        if data_set_size>0:
            #print "DS size: "+str(data_set_size)
            combo_generator=it.combinations(range(0,data_set_size),photo_number)
            #print "CG size: "+str(len(list(combo_generator)))
            #print list(combo_generator)
            #print mark_data
            counter=0
            #print 'reset counter'
            print_pred_counter=0
            for pic_set in combo_generator:
                confidence_mini_list=[]
                mark_pred_mini_list=[]
                for j in range(0,photo_number):
                    confidence_mini_list.append(confidence_data[pic_set[j]])
                    mark_pred_mini_list.append(mark_pred_data[pic_set[j]])
               # print sum(mark_pred_mini_list)
                #print counter
               # print print_pred_counter
                if test_type==0:#zero photo method
                    if sum(mark_pred_mini_list)>=-0.5:
                        print_pred_counter+=1
                if test_type==1:#one photo method
                    if sum(mark_pred_mini_list)>=0.5:
                        print_pred_counter+=1
                if test_type==2:#two photo method
                    if sum(mark_pred_mini_list)>=1.5:
                        print_pred_counter+=1
                if test_type==3:#three photo method
                    if sum(mark_pred_mini_list)>=2.5:
                        print_pred_counter+=1
                if test_type==4:#four photo method
                    if sum(mark_pred_mini_list)>=3.5:
                        print_pred_counter+=1
                if test_type==5:#five photo method
                    if sum(mark_pred_mini_list)>=3.5:
                        print_pred_counter+=1
               #if test_type==0:#one photo method
                #    if sum(mark_pred_mini_list)>=0.5:
                #        print_pred_counter+=1
                #if test_type==20:
                #    if sum(mark_pred_mini_list)==2:
                #        print_pred_counter+=1
                #if test_type==21:
                #    max_confidence=max(confidence_mini_list)
                #    for k in range(0,len(confidence_mini_list)):
                #        if confidence_mini_list[k]==max_confidence:
                #            pred_val_final=mark_pred_mini_list[k]
                #    if pred_val_final==1:
                #        print_pred_counter+=1
                #if test_type==30:#three pics, best two out of three of the mark_pred wins
                #    if sum(mark_pred_mini_list)>1.5:
                #        print_pred_counter+=1
                #if test_type==31:#three pics, best two out of three of the mark_pred wins
                #    if sum(mark_pred_mini_list)>2.5:
                #        print_pred_counter+=1
                #if test_type==32:
                #    max_confidence=max(confidence_mini_list)
                #    for k in range(0,len(confidence_mini_list)):
                #        if confidence_mini_list[k]==max_confidence:
                #            pred_val_final=mark_pred_mini_list[k]
                #    if pred_val_final==1:
                #        print_pred_counter+=1
                #if test_type==33:
                #    avg_pred_val=sum(mark_pred_mini_list)/float(len(mark_pred_mini_list))
                #    if avg_pred_val==0:
                #        null=1;
                #    elif avg_pred_val==1:
                #        print_pred_counter+=1
                #    else: #split into blank and print 
                #        print_vec=[]
                #        blank_vec=[]
                #        for k in range(0,len(mark_pred_mini_list)):
                #            if mark_pred_mini_list[k]==0:
                #                blank_vec.append(confidence_mini_list[k])
                #            elif mark_pred_mini_list[k]==1:
                #                print_vec.append(confidence_mini_list[k])
                #        blank_conf_avg=sum(blank_vec)/float(len(blank_vec))
                #        print_conf_avg=sum(print_vec)/float(len(print_vec))
                #        if print_conf_avg>blank_conf_avg:
                #            print_pred_counter+=1

                #if test_type==4:#three pics, best two out of three of the mark_pred wins
                #    if sum(mark_pred_mini_list)>1.5:
                #        print_pred_counter+=1
                #if test_type==40:#three pics, best two out of three of the mark_pred wins
                #    if sum(mark_pred_mini_list)>2.5:
                #        print_pred_counter+=1
                #if test_type==41:#three pics, best two out of three of the mark_pred wins
                #    if sum(mark_pred_mini_list)>3.5:
                #        print_pred_counter+=1
                #if test_type==42:#three pics, best two out of three of the mark_pred wins
                #    max_confidence=max(confidence_mini_list)
                #    for k in range(0,len(confidence_mini_list)):
                #        if confidence_mini_list[k]==max_confidence:
                #            pred_val_final=mark_pred_mini_list[k]
                #    if pred_val_final==1:
                #        print_pred_counter+=1
                #if test_type==43:
                #    avg_pred_val=sum(mark_pred_mini_list)/float(len(mark_pred_mini_list))
                #    if avg_pred_val==0:
                #        null=1;
                #    elif avg_pred_val==1:
                #        print_pred_counter+=1
                #    else: #split into blank and print 
                #        print_vec=[]
                #        blank_vec=[]
                #        for k in range(0,len(mark_pred_mini_list)):
                #            if mark_pred_mini_list[k]==0:
                #                blank_vec.append(confidence_mini_list[k])
                #            elif mark_pred_mini_list[k]==1:
                #                print_vec.append(confidence_mini_list[k])
                #        blank_conf_avg=sum(blank_vec)/float(len(blank_vec))
                #        print_conf_avg=sum(print_vec)/float(len(print_vec))
                #        if print_conf_avg>blank_conf_avg:
                #            print_pred_counter+=1
                counter+=1
                #print 'update counter'

            if mark_data[0]==0:
                FP+=print_pred_counter
                TN+=counter-print_pred_counter
            elif mark_data[0]==1:
                TP+=print_pred_counter
                FN+=counter-print_pred_counter
            if printer:
                print str(super_counter/float(len(super_list)))+" "+str(TP)+" "+str(FP)+" "+str(TN)+" "+str(FN)+" "+str(data_set_size)+" "+str(counter)
        super_counter+=1;
        

    true_positive_percentage=TP/float(TP+FN)
    false_positive_percentage=FP/float(FP+TN)
    truth=true_positive_percentage-false_positive_percentage
    if printer:
        print "Truth: "+str(truth)
        print "TPP: "+str(true_positive_percentage)
        print "FPP: "+str(false_positive_percentage)
    

    return truth, true_positive_percentage, false_positive_percentage

def logistic_regression(csv_file,x_cols,row_keep, printer,mark_pos=-1):
    data=pd.read_csv(csv_file, header=0)

    for keeper_list in row_keep:
        if len(keeper_list)==2:
            data=data.loc[data[keeper_list[0]].isin(keeper_list[1])]

    drop = range(data.shape[1])

    mark_loc=0
    drop=np.delete(drop,x_cols)
    if mark_pos==-1:
        mark_loc=len(x_cols)-1
    else:
        mark_loc=mark_pos
    data.drop(data.columns[drop], axis=1, inplace=True)
    print(data.head(10))
    data=data.dropna(axis=0,how='any')
  
    y = data.iloc[:,mark_loc]
    #Drop the 4th col for X data
    data.drop(data.columns[[mark_loc]], axis=1, inplace=True)
    X = data.iloc[:,:]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.000, random_state=0)
    y_train.astype('int')
    y_test.astype('int')
    X_train.shape
    classifier = LogisticRegression(solver='newton-cg', random_state = 0,fit_intercept=True,class_weight=None)

    classifier.fit(X_train, y_train)

    y_pred = classifier.predict(X_train)



    from sklearn.metrics import confusion_matrix
            
    confusion_matrix = confusion_matrix(y_train, y_pred)
    #print confusion_matrix
    tn=confusion_matrix[0,0]
    fp=confusion_matrix[0,1]
    tp=confusion_matrix[1,1]
    fn=confusion_matrix[1,0]
    tpr=tp/float(tp+fn)
    tnr=tn/float(tn+fp)
    fpr=fp/float(fp+tn)
    #truth=tpr-(1-tnr)
    truth=tpr-fpr
    
    if printer:
        print 'Truth: ' + str(truth)
        print 'TPP: '+str(tpr)
        print 'fpr: '+str(fpr)

        for row in range(0,len(X_train.index)):
            mark_perc= classifier.predict_proba(X_train.iloc[[row]])[0,1]
            LUX= X_train.iloc[[row]].values[0,14]
            print " ",
            mark= y_train.iloc[[row]].values[0]
            if mark_perc<0.5:
                pred_mark=0
                confidence=(0.5-mark_perc)*2
            else:
                pred_mark=1
                confidence=(mark_perc-0.5)*2
            if pred_mark==mark:
                accuracy=1
            else:
                accuracy=0
            multiple1=100
            multiple2=300
            if LUX<=1000:
                MultLux=np.floor((LUX + multiple1/2) / multiple1) * multiple1
            else:
                MultLux=np.floor((LUX + multiple2/2) / multiple2) * multiple2
            MultLux=int(MultLux)
            print str(mark_perc)+","+str(LUX)+","+str(MultLux)+","+str(mark)+","+str(pred_mark)+","+str(accuracy)+","+str(confidence)

        print(confusion_matrix)
        print y_train.mean()
        print classifier.coef_
        print classifier.intercept_

        print(str(data.shape[0])+', {:.5f}'.format(classifier.score(X_train, y_train)))+","+str(truth)+ "," + str(tpr) + "," + str(fpr) + "," + str(tp) + "," + str(fn) + "," + str(tn) + "," + str(fp)
    return [truth,tpr,fpr,classifier.coef_,classifier.intercept_]

def logistic_regression_prep(csv_file,x_cols,row_keep=[[0]], tst_size=0.000,mark_pos=-1,dataframe_checker=False,dataframe_input=[]):
    if dataframe_checker:
        data=dataframe_input
    else:
        data=pd.read_csv(csv_file, header=0)

    data = data[data.applymap(np.isreal).any(1)]

    for keeper_list in row_keep:
        if len(keeper_list)==2:
            data=data.loc[data[keeper_list[0]].isin(keeper_list[1])]

    drop = range(data.shape[1])

    mark_loc=0
    drop=np.delete(drop,x_cols)
    if mark_pos==-1:
        mark_loc=len(x_cols)-1
    else:
        mark_loc=mark_pos
    data.drop(data.columns[drop], axis=1, inplace=True)
    
    data=data.dropna(axis=0,how='any')
  
    y = data.iloc[:,mark_loc]
    #Drop the 4th col for X data
    data.drop(data.columns[[mark_loc]], axis=1, inplace=True)
    X = data.iloc[:,:]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=tst_size, random_state=0)
    y_train.astype('int')
    y_test.astype('int')
    
    return [X_train,y_train,X_test,y_test]

def adapted_J(sensitivity,specificity,n_print=0,n_CP=0):
    sen_weight=1
    spec_weight=1
    FN_weight=1
    CP_weight=2
    n_FN=(1-sensitivity)*n_print-n_CP
    if n_print==0:
        sen_mod=sensitivity
    else:
        sen_mod=1-(((n_FN*FN_weight)/float(n_print))+((n_CP*CP_weight)/float(n_print)))/float(FN_weight+CP_weight)

    J=2*(sen_weight*sensitivity+spec_weight*specificity)/float(sen_weight+spec_weight)-1
    #J=(sen_weight*sensitivity+spec_weight*specificity)/float(sen_weight+spec_weight)
    return J
    

def cg_dataframe_filter(dataframe_input,formulation,recipe,modification):
    df=copy.copy(dataframe_input)

    #KEEP ROWS THAT MATCH THE FORMULATION OR BLANK
    if not formulation=='skip':
        df=df.loc[df['Formulation'].str.contains(formulation)]
    
    #KEEP ROWS THAT MATCH THE RECIPE
    if not recipe[0]=='skip':
        df=df.loc[df['Ink'].isin([recipe[0]])]
    if not recipe[1]=='skip':
        df=df.loc[df['Binder'].isin([recipe[1]])]
    if not recipe[2]=='skip':
        df=df.loc[df['Solvent'].isin([recipe[2]])]

    #KEEP ROWS THAT MATCH THE MODIFICATION
    if not modification=='skip':
        #make lowercase and uppercase options
        lc_mod=modification.lower()
        uc_mod=modification.upper()
        df_uc=df.loc[df['Mod'].str.contains(lc_mod)]
        df_lc=df.loc[df['Mod'].str.contains(uc_mod)]
        df=pd.concat([df_uc,df_lc])
    return df

def cg_scan_range_finder(dataframe_input,ROI_cols,ROI_size):
    df=copy.copy(dataframe_input)
    #df_print,df_blank=[x for _, x in df.groupby(df['Mark'] <0.5) ]

    #df_range=[df_blank,df_print]
    #max_min_export=[]
    #for df_index in range(len(df_range)):
    #    value_holder=[]
    #    for ROI in range(ROI_size):
    #        for scan in range(ROI_cols):
    #            col_caller='ROI_'+str(ROI)+'_scan_'+str(scan)
    #            if df_index==0:
                    
    #                value_holder.append(df_range[df_index][col_caller].max())
    #            elif df_index==1:
    #                value_holder.append(df_range[df_index][col_caller].min())
    #    if df_index==0:
    #        max_min_export.append(np.max(value_holder))
    #    elif df_index==1:
    #        max_min_export.append(np.min(value_holder))
    max_min_export=[2,-1]
    return max_min_export

def cg_combine_print_blank(dataframe_print,dataframe_blank):
    dfp=copy.copy(dataframe_print)
    dfb=copy.copy(dataframe_blank)
    pLength = dfp.shape[0]
    bLength = dfb.shape[0]
    #print pLength
    #print bLength
    print_mark_series=pd.Series(np.ones(pLength))
    blank_mark_series=pd.Series(np.zeros(bLength))
    dfp=dfp.assign(Mark=print_mark_series.values)
    dfb=dfb.assign(Mark=blank_mark_series.values)
    df_fin=pd.concat([dfp,dfb],ignore_index=True)
    return df_fin

def cg_white_mean_finder(dataframe_input,scan_size=10):
    list_data_holder=cg_dataframe_to_list(dataframe_input,scan_size)
    ROI_blank=[]
    ROI_print=[]
    for row_index in range(len(list_data_holder)):
        sum_count=0
        ROI_holder=[]
        for ROI_index in range(3):
            white_holder=[]
            for scan_index in range(len(list_data_holder[row_index][0][ROI_index])): 
                white_holder.append(list_data_holder[row_index][0][ROI_index][scan_index])
            ROI_mean=np.mean(white_holder)
            ROI_holder.append(ROI_mean)   
        if list_data_holder[row_index][1]==0:
            ROI_blank.append(ROI_holder)
        elif list_data_holder[row_index][1]==1:
            ROI_print.append(ROI_holder)
        else:
            print "************MARK ERROR********"
    ROI0_blank=[]
    ROI1_blank=[]
    ROI2_blank=[]
    ROI0_print=[]
    ROI1_print=[]
    ROI2_print=[]
    for ROI_blank_single in ROI_blank:
        ROI0_blank.append(ROI_blank_single[0])
        ROI1_blank.append(ROI_blank_single[1])
        ROI2_blank.append(ROI_blank_single[2])
    for ROI_print_single in ROI_print:
        ROI0_print.append(ROI_print_single[0])
        ROI1_print.append(ROI_print_single[1])
        ROI2_print.append(ROI_print_single[2])
    ROI0_blank_mean=np.mean(ROI0_blank)
    ROI1_blank_mean=np.mean(ROI1_blank)
    ROI2_blank_mean=np.mean(ROI2_blank)
    ROI0_print_mean=np.mean(ROI0_print)
    ROI1_print_mean=np.mean(ROI1_print)
    ROI2_print_mean=np.mean(ROI2_print)    
    ROI_print_mean=np.mean([ROI0_print_mean,ROI1_print_mean,ROI2_print_mean])
    ROI_blank_mean=np.mean([ROI0_blank_mean,ROI1_blank_mean,ROI2_blank_mean])
    return [[ROI_print_mean,ROI0_print_mean,ROI1_print_mean,ROI2_print_mean],[ROI_blank_mean,ROI0_blank_mean,ROI1_blank_mean,ROI2_blank_mean]]

def cg_redundancy_tester(dataframe_input,best_roi_thresh,best_dec_thresh,best_redundancy,print_failures=False,scan_size=10):
    list_data_holder=cg_dataframe_to_list(dataframe_input,scan_size)
    true_blank_guess_list=[]
    true_print_guess_list=[]
    for row_index in range(len(list_data_holder)):
        sum_count=0
        for ROI_index in range(len(best_roi_thresh)):
            read_count=0
            for scan_index in range(len(list_data_holder[row_index][0][ROI_index])): 
                if list_data_holder[row_index][0][ROI_index][scan_index]>best_roi_thresh[ROI_index]:
                    read_count+=1
            confidence_value=float(read_count)/float(len(list_data_holder[row_index][0][ROI_index]))
            if confidence_value>best_dec_thresh[ROI_index]:
                sum_count+=1
        if sum_count>best_redundancy:
            guess_val=1
        else:
            guess_val=0
        if list_data_holder[row_index][1]==0:
            true_blank_guess_list.append(guess_val)
        elif list_data_holder[row_index][1]==1:
            true_print_guess_list.append(guess_val)
        else:
            print "************MARK ERROR********"
        if print_failures:
            if not guess_val==list_data_holder[row_index][1]:
                print dataframe_input.iloc[[row_index]]
    sensitivity=np.mean(true_print_guess_list)
    specificity=1-np.mean(true_blank_guess_list)
    J=sensitivity+specificity-1
    n_blank=len(true_blank_guess_list)
    n_print=len(true_print_guess_list)

    return [J, sensitivity, specificity, n_print, n_blank]

def cg_redundancy_tester_detail(dataframe_input,best_roi_thresh,best_dec_thresh,best_redundancy,scan_size=10,print_failures=False): #Prints out original dataframe, as well as binary guess for each ROI, and sucess/failure per guess
    #Reset row index of dataframe so that data can be grabbed easily
    dataframe_input=dataframe_input.reset_index(drop=True)
    #Convert to list for speed
    list_data_holder=cg_dataframe_to_list(dataframe_input,scan_size)
    true_blank_guess_list=[]
    true_print_guess_list=[]
    roi_guess_list=[[],[],[]] #only built for 3 ROIs
    roi_accuracy_list=[[],[],[]]
    for row_index in range(len(list_data_holder)):
        #for header_val in ['Formulation','Mod','Ink','Binder','Solvent','DateTime','Mark']:
        #    print dataframe_input[header_val][row_index],
        #    print ',',

        sum_count=0
        for ROI_index in range(len(best_roi_thresh)):
            read_count=0
            for scan_index in range(len(list_data_holder[row_index][0][ROI_index])): 
                if list_data_holder[row_index][0][ROI_index][scan_index]>best_roi_thresh[ROI_index]:
                    read_count+=1
            confidence_value=float(read_count)/float(len(list_data_holder[row_index][0][ROI_index]))
            if confidence_value>best_dec_thresh[ROI_index]:
                sum_count+=1
                if list_data_holder[row_index][1]==1:
                    roi_accuracy_list[ROI_index].append(1)
                else:
                    roi_accuracy_list[ROI_index].append(0)
                #print '1,',
            else:
                if list_data_holder[row_index][1]==1:
                    roi_accuracy_list[ROI_index].append(0)
                else:
                    roi_accuracy_list[ROI_index].append(1)
                #print '0,',

        if sum_count>best_redundancy:
            guess_val=1
        else:
            guess_val=0

        #if guess_val==list_data_holder[row_index][1]:
        #    print '1'
        #else:
        #    print '0'

        if list_data_holder[row_index][1]==0:
            true_blank_guess_list.append(guess_val)
        elif list_data_holder[row_index][1]==1:
            true_print_guess_list.append(guess_val)
        else:
            print "************MARK ERROR********"
        if print_failures:
            if not guess_val==list_data_holder[row_index][1]:
                print dataframe_input.iloc[[row_index]]
    sensitivity=np.mean(true_print_guess_list)
    specificity=1-np.mean(true_blank_guess_list)
    J=sensitivity+specificity-1
    n_blank=len(true_blank_guess_list)
    n_print=len(true_print_guess_list)

    for lst in roi_accuracy_list:
        print np.average(lst),
        print ",",

    return [J, sensitivity, specificity, n_print, n_blank]

def cg_dataframe_to_list(dataframe_input,scan_size):
    header_list=list(dataframe_input)
    #scan_size=10
    ROI_starter_list=["ROI_0_scan_0","ROI_1_scan_0","ROI_2_scan_0","Mark"]
    ROI_starter_index_list=[0,0,0,0]
    for header_index in range(len(header_list)):
        for header_string_index in range(len(ROI_starter_list)):
            if header_list[header_index]==ROI_starter_list[header_string_index]:
                ROI_starter_index_list[header_string_index]=header_index+1

    #print ROI_starter_index_list
    
    #move values from dataframe to list: [[[ROI1][ROI2][ROI3]],[Mark]]
    list_data_holder=[]
    for row in dataframe_input.itertuples():
        #print row
        ROI_list_holder=[]
        for ROI_index in range(len(ROI_starter_list)-1):
            ROI_indi_holder=[]
            for scan_index in range(scan_size):
                ROI_indi_holder.append(row[ROI_starter_index_list[ROI_index]+scan_index])
            ROI_list_holder.append(ROI_indi_holder)
        row_tuple=[ROI_list_holder,row[ROI_starter_index_list[3]]]
        list_data_holder.append(row_tuple)

    return list_data_holder
    

def cg_redundancy_modeler(dataframe_input,scan_size=10):
    scan_range=cg_scan_range_finder(dataframe_input,scan_size,3)
    #gonna sweep over bloody everything, and figure out the J value in each case, then save cases where J value is real good
    scan_n=20;
    ROI0_thresh_rng=np.linspace(scan_range[0],scan_range[1],scan_n)
    ROI1_thresh_rng=np.linspace(scan_range[0],scan_range[1],scan_n)
    ROI2_thresh_rng=np.linspace(scan_range[0],scan_range[1],scan_n)
    ROI0_dec_rng=np.linspace(-0.05,0.95,11)
    ROI1_dec_rng=np.linspace(-0.05,0.95,11)
    ROI2_dec_rng=np.linspace(-0.05,0.95,11) 
    redundancy_range=[0.5,1.5,2.5]
    ROI_thresh_rng_list=[ROI0_thresh_rng,ROI1_thresh_rng,ROI2_thresh_rng]
    ROI_dec_rng_list=[ROI0_dec_rng,ROI1_dec_rng,ROI2_dec_rng]
    

    header_list=list(dataframe_input)
    ROI_starter_list=["ROI_0_scan_0","ROI_1_scan_0","ROI_2_scan_0","Mark"]
    ROI_starter_index_list=[0,0,0,0]
    for header_index in range(len(header_list)):
        for header_string_index in range(len(ROI_starter_list)):
            if header_list[header_index]==ROI_starter_list[header_string_index]:
                ROI_starter_index_list[header_string_index]=header_index+1

    #print ROI_starter_index_list
    
    #move values from dataframe to list: [[[[ROI1][ROI2][ROI3]]],[Mark]]
    list_data_holder=[]
    for row in dataframe_input.itertuples():
        ROI_list_holder=[]
        for ROI_index in range(len(ROI_thresh_rng_list)):
            ROI_indi_holder=[]
            for scan_index in range(scan_size):
                ROI_indi_holder.append(row[ROI_starter_index_list[ROI_index]+scan_index])
            ROI_list_holder.append(ROI_indi_holder)
        row_tuple=[ROI_list_holder,row[ROI_starter_index_list[3]]]
        list_data_holder.append(row_tuple)

    #print list_data_holder
    #first find optimal thresholds for each ROI
    best_roi_thresh=len(ROI_thresh_rng_list)*[-1]
    best_dec_thresh=len(ROI_thresh_rng_list)*[-1]
    best_J=len(ROI_thresh_rng_list)*[-1]
    for ROI_index in range(len(ROI_thresh_rng_list)):
        for ROI_thresh in ROI_thresh_rng_list[ROI_index]:
            #make two new lists - blank confidence and print confidence
            print_confidence=[]
            blank_confidence=[]
            for row_index in range(len(list_data_holder)):
                #print row
                #print type(row)
                read_count=0
                for scan_index in range(len(list_data_holder[row_index][0][ROI_index])):
                    #col_caller='ROI_'+str(ROI_index)+'_scan_'+str(scan_index)
                    
                    if list_data_holder[row_index][0][ROI_index][scan_index]>ROI_thresh:
                        read_count+=1
                confidence_value=float(read_count)/float(scan_size)
                row_marker=list_data_holder[row_index][1]
                #print row_marker
                if row_marker==1:
                    print_confidence.append(confidence_value)
                elif row_marker==0:
                    blank_confidence.append(confidence_value)
                else:
                    print "***********MARKER MISSING ERROR*********"
            ## now that the confidence lists are done, we get ROI accuracy using dec_rng
            
            for ROI_dec in ROI_dec_rng_list[ROI_index]:
                print_binary_list=np.zeros(len(print_confidence))
                blank_binary_list=np.zeros(len(blank_confidence))

                #set to 1 if value is greater than threshold
                print_binary_list[print_confidence>ROI_dec]=1
                blank_binary_list[blank_confidence>ROI_dec]=1



                sensitivity=np.mean(print_binary_list)
                specificity=1-np.mean(blank_binary_list)
                J=sensitivity+specificity-1

                if J>best_J[ROI_index]:
                    best_J[ROI_index]=J
                    best_roi_thresh[ROI_index]=ROI_thresh
                    best_dec_thresh[ROI_index]=ROI_dec
                    #print ROI_index,
                    #print ",",
                    #print best_J[ROI_index],
                    #print ",",
                    #print sensitivity,
                    #print ",",
                    #print specificity,
                    #print ",",
                    #print best_roi_thresh[ROI_index],
                    #print ",",
                    #print best_dec_thresh[ROI_index]
    #print best_J
    #print best_dec_thresh
    #print best_roi_thresh

    #now figure out the best level of redundancy
    print_sum=[]
    blank_sum=[]
    for row in dataframe_input.itertuples():
        sum=0
        for ROI_index in range(len(ROI_thresh_rng_list)):
            ROI_thresh=best_roi_thresh[ROI_index]
            dec_thresh=best_dec_thresh[ROI_index]
            read_count=0
            for scan_index in range(scan_size):
                #col_caller='ROI_'+str(ROI_index)+'_scan_'+str(scan_index)
                    
                if row[ROI_starter_index_list[ROI_index]+scan_index]>ROI_thresh:
                    read_count+=1
            confidence_value=float(read_count)/float(scan_size)
            if confidence_value>dec_thresh:
                sum+=1
        row_marker=row[ROI_starter_index_list[3]]
        #print row_marker
        if row_marker==1:
            print_sum.append(sum)
        elif row_marker==0:
            blank_sum.append(sum)
        else:
            print "***********MARKER MISSING ERROR*********"
    #print print_sum
    #print blank_sum
    ## now that the confidence lists are done, we get ROI accuracy using dec_rng
    best_redundancy=-1
    best_J=-1
    best_sensitivity=-1
    best_specificity=-1
    for redundancy in redundancy_range:
        print_binary_list=np.zeros(len(print_sum))
        blank_binary_list=np.zeros(len(blank_sum))

        #print redundancy
        #print print_sum
        #print print_binary_list
        #print blank_binary_list
        #set to 1 if value is greater than threshold
        for print_index in range(len(print_sum)):
            if print_sum[print_index]>redundancy:
                print_binary_list[print_index]=1

        for blank_index in range(len(blank_sum)):
            if blank_sum[blank_index]>redundancy:
                blank_binary_list[blank_index]=1

        #    print_binary_list[print_sum>redundancy]=1
        #blank_binary_list[blank_sum>redundancy]=1

        #print print_binary_list
        #print blank_binary_list

        sensitivity=np.mean(print_binary_list)
        specificity=1-np.mean(blank_binary_list)
        J=sensitivity+specificity-1

        #print redundancy,
        #print ",",
        #print J,
        #print ",",
        #print sensitivity,
        #print ",",
        #print specificity

        if J>best_J:
            best_J=J
            best_redundancy=redundancy
            best_sensitivity=sensitivity
            best_specificity=specificity


    #print "*********END*********"
    return [[best_J,best_sensitivity,best_specificity,len(print_sum),len(blank_sum)],best_roi_thresh,best_dec_thresh,best_redundancy]

def cg_redundancy_modeler_v2(dataframe_input,scan_size=10):
    scan_range=cg_scan_range_finder(dataframe_input,scan_size,3)
    #gonna sweep over bloody everything, and figure out the J value in each case, then save cases where J value is real good
    scan_n=20;
    #print scan_range[0]+3
    #print scan_range[1]-3
    ROI0_thresh_rng=np.linspace(scan_range[0],scan_range[1],scan_n)
    ROI1_thresh_rng=np.linspace(scan_range[0],scan_range[1],scan_n)
    ROI2_thresh_rng=np.linspace(scan_range[0],scan_range[1],scan_n)
    ROI0_dec_rng=np.linspace(-0.05,0.95,11)
    ROI1_dec_rng=np.linspace(-0.05,0.95,11)
    ROI2_dec_rng=np.linspace(-0.05,0.95,11) 
    redundancy_range=[0.5,1.5,2.5]
    ROI_thresh_rng_list=[ROI0_thresh_rng,ROI1_thresh_rng,ROI2_thresh_rng]
    ROI_dec_rng_list=[ROI0_dec_rng,ROI1_dec_rng,ROI2_dec_rng]

    header_list=list(dataframe_input)
    ROI_starter_list=["ROI_0_scan_0","ROI_1_scan_0","ROI_2_scan_0","Mark"]
    ROI_starter_index_list=[0,0,0,0]
    for header_index in range(len(header_list)):
        for header_string_index in range(len(ROI_starter_list)):
            if header_list[header_index]==ROI_starter_list[header_string_index]:
                ROI_starter_index_list[header_string_index]=header_index+1

    #print ROI_starter_index_list
    
    #move values from dataframe to list: [[[[ROI1][ROI2][ROI3]]],[Mark]]
    list_data_holder=[]
    for row in dataframe_input.itertuples():
        ROI_list_holder=[]
        for ROI_index in range(len(ROI_thresh_rng_list)):
            ROI_indi_holder=[]
            for scan_index in range(scan_size):
                ROI_indi_holder.append(row[ROI_starter_index_list[ROI_index]+scan_index])
            ROI_list_holder.append(ROI_indi_holder)
        row_tuple=[ROI_list_holder,row[ROI_starter_index_list[3]]]
        list_data_holder.append(row_tuple)


    #print list_data_holder
    #first find optimal thresholds for each ROI
    best_roi_thresh=len(ROI_thresh_rng_list)*[-1]
    best_dec_thresh=len(ROI_thresh_rng_list)*[-1]
    best_J=len(ROI_thresh_rng_list)*[-1]
    for ROI_index in range(len(ROI_thresh_rng_list)):
        for ROI_thresh in ROI_thresh_rng_list[ROI_index]:
            #make two new lists - blank confidence and print confidence
            print_confidence=[]
            blank_confidence=[]
            for row_index in range(len(list_data_holder)):
                #print row
                #print type(row)
                read_count=0
                for scan_index in range(len(list_data_holder[row_index][0][ROI_index])):
                    #col_caller='ROI_'+str(ROI_index)+'_scan_'+str(scan_index)
                    
                    if list_data_holder[row_index][0][ROI_index][scan_index]>ROI_thresh:
                        read_count+=1
                confidence_value=float(read_count)/float(scan_size)
                row_marker=list_data_holder[row_index][1]
                #print row_marker
                if row_marker==1:
                    print_confidence.append(confidence_value)
                elif row_marker==0:
                    blank_confidence.append(confidence_value)
                else:
                    print "***********MARKER MISSING ERROR*********"
            ## now that the confidence lists are done, we get ROI accuracy using dec_rng
            
            for ROI_dec in ROI_dec_rng_list[ROI_index]:
                print_binary_list=np.zeros(len(print_confidence))
                blank_binary_list=np.zeros(len(blank_confidence))

                #set to 1 if value is greater than threshold
                print_binary_list[print_confidence>ROI_dec]=1
                blank_binary_list[blank_confidence>ROI_dec]=1



                sensitivity=np.mean(print_binary_list)
                specificity=1-np.mean(blank_binary_list)
                J=adapted_J(sensitivity,specificity)
                #J=sensitivity+specificity-1

                if J>best_J[ROI_index]:
                    T_list=[]
                    D_list=[]
                    best_J[ROI_index]=J
                    T_list.append(ROI_thresh)
                    D_list.append(ROI_dec)
                    #best_roi_thresh[ROI_index]=ROI_thresh
                    #best_dec_thresh[ROI_index]=ROI_dec
                elif J==best_J[ROI_index]:
                    T_list.append(ROI_thresh)
                    D_list.append(ROI_dec)
        #once all threshold-dec pairs have been tried, take median of each of T_list and D_list vectors
        best_roi_thresh[ROI_index]=np.median(T_list)
        best_dec_thresh[ROI_index]=np.median(D_list)
        #print len(T_list)
        #print len(D_list)

    #print [best_J,best_roi_thresh,best_dec_thresh]
    scan_n=100
    T_swing=0.5
    D_swing=0.4
    ROI0_thresh_rng=np.linspace(best_roi_thresh[0]-T_swing,best_roi_thresh[0]+T_swing,scan_n)
    ROI1_thresh_rng=np.linspace(best_roi_thresh[1]-T_swing,best_roi_thresh[1]+T_swing,scan_n)
    ROI2_thresh_rng=np.linspace(best_roi_thresh[2]-T_swing,best_roi_thresh[2]+T_swing,scan_n)
    ROI0_dec_rng=np.arange(np.max([-0.05,best_dec_thresh[0]-D_swing]),np.min([0.95,best_dec_thresh[0]+D_swing])+0.1,0.1)
    ROI1_dec_rng=np.arange(np.max([-0.05,best_dec_thresh[1]-D_swing]),np.min([0.95,best_dec_thresh[1]+D_swing])+0.1,0.1)
    ROI2_dec_rng=np.arange(np.max([-0.05,best_dec_thresh[2]-D_swing]),np.min([0.95,best_dec_thresh[2]+D_swing])+0.1,0.1)
    #print ROI0_dec_rng
    ROI_thresh_rng_list=[ROI0_thresh_rng,ROI1_thresh_rng,ROI2_thresh_rng]
    ROI_dec_rng_list=[ROI0_dec_rng,ROI1_dec_rng,ROI2_dec_rng]
        #print list_data_holder
    #first find optimal thresholds for each ROI
    best_roi_thresh=len(ROI_thresh_rng_list)*[-1]
    best_dec_thresh=len(ROI_thresh_rng_list)*[-1]
    #best_J=len(ROI_thresh_rng_list)*[-1]
    for ROI_index in range(len(ROI_thresh_rng_list)):
        T_list=[]
        D_list=[]
        for ROI_thresh in ROI_thresh_rng_list[ROI_index]:
            #make two new lists - blank confidence and print confidence
            print_confidence=[]
            blank_confidence=[]
            for row_index in range(len(list_data_holder)):
                #print row
                #print type(row)
                read_count=0
                for scan_index in range(len(list_data_holder[row_index][0][ROI_index])):
                    #col_caller='ROI_'+str(ROI_index)+'_scan_'+str(scan_index)
                    
                    if list_data_holder[row_index][0][ROI_index][scan_index]>ROI_thresh:
                        read_count+=1
                confidence_value=float(read_count)/float(scan_size)
                row_marker=list_data_holder[row_index][1]
                #print row_marker
                if row_marker==1:
                    print_confidence.append(confidence_value)
                elif row_marker==0:
                    blank_confidence.append(confidence_value)
                else:
                    print "***********MARKER MISSING ERROR*********"
            ## now that the confidence lists are done, we get ROI accuracy using dec_rng
            
            for ROI_dec in ROI_dec_rng_list[ROI_index]:
                print_binary_list=np.zeros(len(print_confidence))
                blank_binary_list=np.zeros(len(blank_confidence))

                #set to 1 if value is greater than threshold
                print_binary_list[print_confidence>ROI_dec]=1
                blank_binary_list[blank_confidence>ROI_dec]=1



                sensitivity=np.mean(print_binary_list)
                specificity=1-np.mean(blank_binary_list)
                J=sensitivity+specificity-1
                J=adapted_J(sensitivity,specificity)

                if J>best_J[ROI_index]-0.05:
                    T_list.append(ROI_thresh)
                    D_list.append(ROI_dec)
        #once all threshold-dec pairs have been tried, take median of each of T_list and D_list vectors
        best_roi_thresh[ROI_index]=np.median(T_list)
        best_dec_thresh[ROI_index]=np.median(D_list)
        #print len(T_list)
        #print len(D_list)


                    #print ROI_index,
                    #print ",",
                    #print best_J[ROI_index],
                    #print ",",
                    #print sensitivity,
                    #print ",",
                    #print specificity,
                    #print ",",
                    #print ROI_thresh,
                    #print ",",
                    #print ROI_dec
    #print best_J
    #print best_dec_thresh
    #print best_roi_thresh

    #now figure out the best level of redundancy
    print_sum=[]
    blank_sum=[]
    for row in dataframe_input.itertuples():
        sum=0
        for ROI_index in range(len(ROI_thresh_rng_list)):
            ROI_thresh=best_roi_thresh[ROI_index]
            dec_thresh=best_dec_thresh[ROI_index]
            read_count=0
            for scan_index in range(scan_size):
                #col_caller='ROI_'+str(ROI_index)+'_scan_'+str(scan_index)
                    
                if row[ROI_starter_index_list[ROI_index]+scan_index]>ROI_thresh:
                    read_count+=1
            confidence_value=float(read_count)/float(scan_size)
            if confidence_value>dec_thresh:
                sum+=1
        row_marker=row[ROI_starter_index_list[3]]
        #print row_marker
        if row_marker==1:
            print_sum.append(sum)
        elif row_marker==0:
            blank_sum.append(sum)
        else:
            print "***********MARKER MISSING ERROR*********"
    #print print_sum
    #print blank_sum
    ## now that the confidence lists are done, we get ROI accuracy using dec_rng
    best_redundancy=-1
    best_J=-1
    best_sensitivity=-1
    best_specificity=-1
    for redundancy in redundancy_range:
        print_binary_list=np.zeros(len(print_sum))
        blank_binary_list=np.zeros(len(blank_sum))

        #print redundancy
        #print print_sum
        #print print_binary_list
        #print blank_binary_list
        #set to 1 if value is greater than threshold
        for print_index in range(len(print_sum)):
            if print_sum[print_index]>redundancy:
                print_binary_list[print_index]=1

        for blank_index in range(len(blank_sum)):
            if blank_sum[blank_index]>redundancy:
                blank_binary_list[blank_index]=1

        #    print_binary_list[print_sum>redundancy]=1
        #blank_binary_list[blank_sum>redundancy]=1

        #print print_binary_list
        #print blank_binary_list

        sensitivity=np.mean(print_binary_list)
        specificity=1-np.mean(blank_binary_list)
        J=sensitivity+specificity-1

        #print redundancy,
        #print ",",
        #print J,
        #print ",",
        #print sensitivity,
        #print ",",
        #print specificity

        if J>best_J:
            best_J=J
            best_redundancy=redundancy
            best_sensitivity=sensitivity
            best_specificity=specificity


    #print "*********END*********"
    return [[best_J,best_sensitivity,best_specificity,len(print_sum),len(blank_sum)],best_roi_thresh,best_dec_thresh,best_redundancy]

def cg_redundancy_modeler_v3(dataframe_input,scan_size=10,roi_total=3,):
    scan_range=cg_scan_range_finder(dataframe_input,scan_size,3)
    #gonna sweep over bloody everything, and figure out the J value in each case, then save cases where J value is real good
    scan_n=20;
    #print scan_range[0]+3
    #print scan_range[1]-3
    ROI0_thresh_rng=np.linspace(scan_range[0],scan_range[1],scan_n)
    ROI1_thresh_rng=np.linspace(scan_range[0],scan_range[1],scan_n)
    ROI2_thresh_rng=np.linspace(scan_range[0],scan_range[1],scan_n)
    ROI0_dec_rng=np.linspace(-0.05,0.95,11)
    ROI1_dec_rng=np.linspace(-0.05,0.95,11)
    ROI2_dec_rng=np.linspace(-0.05,0.95,11) 
    redundancy_range=np.linspace(0.5,roi_total-0.5,roi_total)
    ROI_thresh_rng_list=[ROI0_thresh_rng,ROI1_thresh_rng,ROI2_thresh_rng]
    ROI_dec_rng_list=[ROI0_dec_rng,ROI1_dec_rng,ROI2_dec_rng]

    #New code that can accomidate n number of ROIs
    ROI_thresh_rng_list=[]
    ROI_thresh_basis=np.linspace(scan_range[0],scan_range[1],scan_n)
    ROI_dec_rng_list=[]
    ROI_dec_basis=np.linspace(-0.05,0.95,scan_size+1)

    for roi_iterator in range(roi_total):
        ROI_thresh_rng_list.append(ROI_thresh_basis)
        ROI_dec_rng_list.append(ROI_dec_basis)




    header_list=list(dataframe_input)
    ROI_starter_list=["ROI_0_scan_0","ROI_1_scan_0","ROI_2_scan_0","Mark"]
    ROI_starter_list=[]
    ROI_starter_index_list=[]
    for roi_iterator in range(roi_total):
        ROI_starter_list.append("ROI_"+str(roi_iterator)+"_scan_0")
        ROI_starter_index_list.append(0)
    ROI_starter_list.append("Mark")
    ROI_starter_index_list.append(0)
    #ROI_starter_index_list=[0,0,0,0]
    for header_index in range(len(header_list)):
        for header_string_index in range(len(ROI_starter_list)):
            if header_list[header_index]==ROI_starter_list[header_string_index]:
                ROI_starter_index_list[header_string_index]=header_index+1

    #print ROI_starter_index_list
    
   

    #move values from dataframe to list: [[[[ROI1][ROI2][ROI3]]],[Mark]]
    list_data_holder=[]
    for row in dataframe_input.itertuples():
        ROI_list_holder=[]
        for ROI_index in range(len(ROI_thresh_rng_list)):
            ROI_indi_holder=[]
            for scan_index in range(scan_size):
                ROI_indi_holder.append(row[ROI_starter_index_list[ROI_index]+scan_index])
            ROI_list_holder.append(ROI_indi_holder)
        row_tuple=[ROI_list_holder,row[ROI_starter_index_list[-1]]]
        list_data_holder.append(row_tuple)


    #print list_data_holder

    #iter_temp=0
    #for row in list_data_holder:
    #    print row[1],
    #    print "  "+str(iter_temp)
    #    iter_temp+=1


    #first find optimal thresholds for each ROI
    best_roi_thresh=len(ROI_thresh_rng_list)*[-1]
    best_dec_thresh=len(ROI_thresh_rng_list)*[-1]
    best_J=len(ROI_thresh_rng_list)*[-1]
    for ROI_index in range(len(ROI_thresh_rng_list)):
        for ROI_thresh in ROI_thresh_rng_list[ROI_index]:
            #make two new lists - blank confidence and print confidence
            print_confidence=[]
            blank_confidence=[]
            for row_index in range(len(list_data_holder)):
                #print row
                #print type(row)
                read_count=0
                for scan_index in range(len(list_data_holder[row_index][0][ROI_index])):
                    #col_caller='ROI_'+str(ROI_index)+'_scan_'+str(scan_index)
                    
                    if list_data_holder[row_index][0][ROI_index][scan_index]>ROI_thresh:
                        read_count+=1
                confidence_value=float(read_count)/float(scan_size)
                row_marker=list_data_holder[row_index][1]
                #print row_marker
                if row_marker==1:
                    print_confidence.append(confidence_value)
                elif row_marker==0:
                    blank_confidence.append(confidence_value)
                else:
                    print "***********MARKER MISSING ERROR1*********"
            ## now that the confidence lists are done, we get ROI accuracy using dec_rng
            
            for ROI_dec in ROI_dec_rng_list[ROI_index]:
                print_binary_list=np.zeros(len(print_confidence))
                blank_binary_list=np.zeros(len(blank_confidence))

                #set to 1 if value is greater than threshold
                print_binary_list[print_confidence>ROI_dec]=1
                blank_binary_list[blank_confidence>ROI_dec]=1



                sensitivity=np.mean(print_binary_list)
                specificity=1-np.mean(blank_binary_list)
                J=adapted_J(sensitivity,specificity)
                #J=sensitivity+specificity-1

                if J>best_J[ROI_index]:
                    T_list=[]
                    D_list=[]
                    best_J[ROI_index]=J
                    T_list.append(ROI_thresh)
                    D_list.append(ROI_dec)
                    #best_roi_thresh[ROI_index]=ROI_thresh
                    #best_dec_thresh[ROI_index]=ROI_dec
                elif J==best_J[ROI_index]:
                    T_list.append(ROI_thresh)
                    D_list.append(ROI_dec)
        #once all threshold-dec pairs have been tried, take median of each of T_list and D_list vectors
        best_roi_thresh[ROI_index]=np.median(T_list)
        best_dec_thresh[ROI_index]=np.median(D_list)
        #print len(T_list)
        #print len(D_list)

    #print [best_J,best_roi_thresh,best_dec_thresh]
    scan_n=100
    T_swing=0.5
    D_swing=0.4
    ROI0_thresh_rng=np.linspace(best_roi_thresh[0]-T_swing,best_roi_thresh[0]+T_swing,scan_n)
    ROI1_thresh_rng=np.linspace(best_roi_thresh[1]-T_swing,best_roi_thresh[1]+T_swing,scan_n)
    ROI2_thresh_rng=np.linspace(best_roi_thresh[2]-T_swing,best_roi_thresh[2]+T_swing,scan_n)
    ROI0_dec_rng=np.arange(np.max([-0.05,best_dec_thresh[0]-D_swing]),np.min([0.95,best_dec_thresh[0]+D_swing])+0.1,0.1)
    ROI1_dec_rng=np.arange(np.max([-0.05,best_dec_thresh[1]-D_swing]),np.min([0.95,best_dec_thresh[1]+D_swing])+0.1,0.1)
    ROI2_dec_rng=np.arange(np.max([-0.05,best_dec_thresh[2]-D_swing]),np.min([0.95,best_dec_thresh[2]+D_swing])+0.1,0.1)
    #print ROI0_dec_rng
    ROI_thresh_rng_list=[ROI0_thresh_rng,ROI1_thresh_rng,ROI2_thresh_rng]
    ROI_dec_rng_list=[ROI0_dec_rng,ROI1_dec_rng,ROI2_dec_rng]

    #New code that can accomidate n number of ROIs
    ROI_thresh_rng_list=[]
    ROI_thresh_basis=np.linspace(scan_range[0],scan_range[1],scan_n)
    ROI_dec_rng_list=[]
    ROI_dec_basis=np.linspace(-0.05,0.95,scan_size+1)

    for roi_iterator in range(roi_total):
        thresh_list_temp=np.linspace(best_roi_thresh[roi_iterator]-T_swing,best_roi_thresh[roi_iterator]+T_swing,scan_n)
        ROI_thresh_rng_list.append(thresh_list_temp)
        dec_list_temp=np.arange(np.max([-0.05,best_dec_thresh[roi_iterator]-D_swing]),np.min([0.95,best_dec_thresh[roi_iterator]+D_swing])+0.1,0.1)
        ROI_dec_rng_list.append(dec_list_temp)




        #print list_data_holder
    #first find optimal thresholds for each ROI
    best_roi_thresh=len(ROI_thresh_rng_list)*[-1]
    best_dec_thresh=len(ROI_thresh_rng_list)*[-1]
    #best_J=len(ROI_thresh_rng_list)*[-1]
    for ROI_index in range(len(ROI_thresh_rng_list)):
        T_list=[]
        D_list=[]
        for ROI_thresh in ROI_thresh_rng_list[ROI_index]:
            #make two new lists - blank confidence and print confidence
            print_confidence=[]
            blank_confidence=[]
            for row_index in range(len(list_data_holder)):
                #print row
                #print type(row)
                read_count=0
                for scan_index in range(len(list_data_holder[row_index][0][ROI_index])):
                    #col_caller='ROI_'+str(ROI_index)+'_scan_'+str(scan_index)
                    
                    if list_data_holder[row_index][0][ROI_index][scan_index]>ROI_thresh:
                        read_count+=1
                confidence_value=float(read_count)/float(scan_size)
                row_marker=list_data_holder[row_index][1]
                #print row_marker
                if row_marker==1:
                    print_confidence.append(confidence_value)
                elif row_marker==0:
                    blank_confidence.append(confidence_value)
                else:
                    print "***********MARKER MISSING ERROR2*********"
            ## now that the confidence lists are done, we get ROI accuracy using dec_rng
            
            for ROI_dec in ROI_dec_rng_list[ROI_index]:
                print_binary_list=np.zeros(len(print_confidence))
                blank_binary_list=np.zeros(len(blank_confidence))

                #set to 1 if value is greater than threshold
                print_binary_list[print_confidence>ROI_dec]=1
                blank_binary_list[blank_confidence>ROI_dec]=1



                sensitivity=np.mean(print_binary_list)
                specificity=1-np.mean(blank_binary_list)
                J=sensitivity+specificity-1
                J=adapted_J(sensitivity,specificity)

                if J>best_J[ROI_index]-0.05:
                    T_list.append(ROI_thresh)
                    D_list.append(ROI_dec)
        #once all threshold-dec pairs have been tried, take median of each of T_list and D_list vectors
        best_roi_thresh[ROI_index]=np.median(T_list)
        best_dec_thresh[ROI_index]=np.median(D_list)
        #print len(T_list)
        #print len(D_list)


                    #print ROI_index,
                    #print ",",
                    #print best_J[ROI_index],
                    #print ",",
                    #print sensitivity,
                    #print ",",
                    #print specificity,
                    #print ",",
                    #print ROI_thresh,
                    #print ",",
                    #print ROI_dec
    #print best_J
    #print best_dec_thresh
    #print best_roi_thresh

    #now figure out the best level of redundancy
    print_sum=[]
    blank_sum=[]
    for row in dataframe_input.itertuples():
        sum=0
        for ROI_index in range(len(ROI_thresh_rng_list)):
            ROI_thresh=best_roi_thresh[ROI_index]
            dec_thresh=best_dec_thresh[ROI_index]
            read_count=0
            for scan_index in range(scan_size):
                #col_caller='ROI_'+str(ROI_index)+'_scan_'+str(scan_index)
                    
                if row[ROI_starter_index_list[ROI_index]+scan_index]>ROI_thresh:
                    read_count+=1
            confidence_value=float(read_count)/float(scan_size)
            if confidence_value>dec_thresh:
                sum+=1
        row_marker=row[ROI_starter_index_list[-1]]
        #print row_marker
        if row_marker==1:
            print_sum.append(sum)
        elif row_marker==0:
            blank_sum.append(sum)
        else:
            print "***********MARKER MISSING ERROR3*********"
    #print print_sum
    #print blank_sum
    ## now that the confidence lists are done, we get ROI accuracy using dec_rng
    best_redundancy=-1
    best_J=-1
    best_sensitivity=-1
    best_specificity=-1
    for redundancy in redundancy_range:
        print_binary_list=np.zeros(len(print_sum))
        blank_binary_list=np.zeros(len(blank_sum))

        #print redundancy
        #print print_sum
        #print print_binary_list
        #print blank_binary_list
        #set to 1 if value is greater than threshold
        for print_index in range(len(print_sum)):
            if print_sum[print_index]>redundancy:
                print_binary_list[print_index]=1

        for blank_index in range(len(blank_sum)):
            if blank_sum[blank_index]>redundancy:
                blank_binary_list[blank_index]=1

        #    print_binary_list[print_sum>redundancy]=1
        #blank_binary_list[blank_sum>redundancy]=1

        #print print_binary_list
        #print blank_binary_list

        sensitivity=np.mean(print_binary_list)
        specificity=1-np.mean(blank_binary_list)
        J=sensitivity+specificity-1

        #print redundancy,
        #print ",",
        #print J,
        #print ",",
        #print sensitivity,
        #print ",",
        #print specificity

        if J>best_J:
            best_J=J
            best_redundancy=redundancy
            best_sensitivity=sensitivity
            best_specificity=specificity


    #print "*********END*********"
    return [[best_J,best_sensitivity,best_specificity,len(print_sum),len(blank_sum)],best_roi_thresh,best_dec_thresh,best_redundancy]

def logistic_regression_prep_cg(dataframe_input,dataframe_blank,ROI,ROI_max,combine_scan_data=True):
    df=copy.copy(dataframe_input)

    #PULL OUT THE DATA YOU WANT
    print_list=[]
    blank_list=[]
    for index in range(ROI_max):
        col_caller='ROI_'+str(ROI)+'_scan_'+str(index)
        print_list.extend(df[col_caller].tolist())
        blank_list.extend(dataframe_blank[col_caller].tolist())

    print_y_val=len(print_list)*[1]
    blank_y_val=len(blank_list)*[0]

    x_col_list=[]
    x_col_list.extend(blank_list)
    x_col_list.extend(print_list)

    y_col_list=[]
    y_col_list.extend(print_y_val)
    y_col_list.extend(blank_y_val)

    y_mean=np.mean(print_list)
    x_mean=np.mean(blank_list)
    print x_mean,
    print ",",
    #print len(x_col_list)
    #print len(y_col_list)

    #x_col_df=pd.DataFrame({'ROI_'+str(ROI):x_col_list})
    x_col_df=pd.DataFrame({'ROI':x_col_list})
    y_col_df=pd.DataFrame({'Mark':y_col_list})


    
    return [x_col_df,y_col_df]


def logistic_regression_model(X_train,y_train, printer=False,tester_switch=False,xTst=[],yTst=[],overfitting_analysis=False,confidence_table=False):
   
    classifier = LogisticRegression(solver='newton-cg', random_state = 0,fit_intercept=True,class_weight="balanced")

    classifier.fit(X_train, y_train)

    if tester_switch:
        X_train=xTst
        y_train=yTst

    y_pred = classifier.predict(X_train)
    if overfitting_analysis:
        from sklearn.model_selection import cross_validate
        from sklearn.metrics import recall_score,f1_score,log_loss,roc_auc_score
        from sklearn.metrics import mean_squared_error
        scoring=['recall','neg_mean_squared_error','f1','neg_log_loss','roc_auc']
        scores=cross_validate(classifier,X_train,y_train,scoring=scoring,cv=10,return_train_score=False)
        print np.average(scores['test_recall']),
        print ",",
        print np.average(scores['test_neg_mean_squared_error']),
        print ",",
        print np.average(scores['test_f1']),
        print ",",
        print np.average(scores['test_neg_log_loss']),
        print ",",
        print np.average(scores['test_roc_auc']),
    


        from sklearn.metrics import classification_report
        report=classification_report(y_train,y_pred,digits=4)
        print report

    from sklearn.metrics import confusion_matrix
    confusion_matrix = confusion_matrix(y_train, y_pred) 
    #print confusion_matrix
    tn=confusion_matrix[0,0]
    fp=confusion_matrix[0,1]
    tp=confusion_matrix[1,1]
    fn=confusion_matrix[1,0]
    tpr=float(tp)/float(tp+fn)
    tnr=float(tn)/float(tn+fp)
    sensitivity=float(tp)/float(tp+fn)
    specificity=float(tn)/float(tn+fp)
    fpr=fp/float(fp+tn)
    #truth=tpr-(1-tnr)
    J=sensitivity+specificity-1
    truth=J
    
    #if printer:
    #    print 'Truth: ' + str(truth)
    #    print 'TPP: '+str(tpr)
    #    print 'fpr: '+str(fpr)

    if confidence_table:
        for row in range(0,len(X_train.index)):
            mark_perc= classifier.predict_proba(X_train.iloc[[row]])[0,1]
            LUX= X_train.iloc[[row]].values[0,14]
            print " ",
            mark= y_train.iloc[[row]].values[0]
            if mark_perc<0.5:
                pred_mark=0
                confidence=(0.5-mark_perc)*2
            else:
                pred_mark=1
                confidence=(mark_perc-0.5)*2
            if pred_mark==mark:
                accuracy=1
            else:
                accuracy=0
            multiple1=100
            multiple2=300
            if LUX<=1000:
                MultLux=np.floor((LUX + multiple1/2) / multiple1) * multiple1
            else:
                MultLux=np.floor((LUX + multiple2/2) / multiple2) * multiple2
            MultLux=int(MultLux)
            print str(mark_perc)+","+str(LUX)+","+str(MultLux)+","+str(mark)+","+str(pred_mark)+","+str(accuracy)+","+str(confidence)

        print(confusion_matrix)
        print y_train.mean()
        print classifier.coef_
        print classifier.intercept_

    if printer:
        print(str(data.shape[0])+', {:.5f}'.format(classifier.score(X_train, y_train)))+","+str(truth)+ "," + str(tpr) + "," + str(fpr) + "," + str(tp) + "," + str(fn) + "," + str(tn) + "," + str(fp)
    return [J,sensitivity,specificity,classifier.coef_,classifier.intercept_]

def sm_logistic_regression_model(X_train,y_train, printer=False,tester_switch=False,xTst=[],yTst=[]):
   
    X_train=sm_tool.add_constant(X_train)

    classifier = sm.Logit(y_train,X_train)

    result=classifier.fit(disp=0,warn_convergence=False)

    coeffs=result.params.values

    #print coeffs
    if printer:
        print "space"
        print result.summary()

        print result.pred_table(0.5)
    
    
    
    prediction_train=result.predict(X_train)
    
    pred_train=sm_logistic_model_tester(prediction_train,y_train)
    #print pred_train
    if not len(xTst)==0:
        xTst=sm_tool.add_constant(xTst)
        prediction_test=result.predict(xTst)
    
        pred_test=sm_logistic_model_tester(prediction_test,yTst)
        if printer:

            print len(prediction_train)
            print len(prediction_test)

   
        #print pred_test
        print min([pred_train[0],pred_test[0]]),
        print "]",
        print pred_train[0],
        print "]",
        print pred_test[0],
        print "]",
        print pred_test[1],
        print "]",
        print pred_test[2],
        print "]",
        print pred_train[1],
        print "]",
        print pred_train[2]
        #print prediction

        return [pred_train[0],pred_test[0],pred_test[1],pred_test[2],pred_train[1],pred_train[2]]
    else:
        return[pred_train[0],pred_train[1],pred_train[2]]

def sm_logistic_model_tester(mark_perc_vec,y_train):
    y_train_list=y_train.values.tolist()
    #print y_train_list
    if not len(mark_perc_vec)==len(y_train_list):
        print "**********ERROR**********"
        print len(mark_perc_vec)
        print len(y_train_list)
    tp_counter=0;
    fp_counter=0;
    tn_counter=0;
    fn_counter=0;
    accuracy_holder=[]
    for index in range(len(mark_perc_vec)):
        if y_train_list[index]==0:
            if mark_perc_vec[index]>0.5:
                fp_counter+=1
                accuracy_holder.append(0)
            elif mark_perc_vec[index]<=0.5:
                tn_counter+=1
                accuracy_holder.append(1)
        elif y_train_list[index]==1:
            if mark_perc_vec[index]>0.5:
                tp_counter+=1
                accuracy_holder.append(1)
            elif mark_perc_vec[index]<=0.5:
                fn_counter+=1
                accuracy_holder.append(0)
    Sen=tp_counter/float(tp_counter+fn_counter)
    Spec=tn_counter/float(fp_counter+tn_counter)
    J=Sen+Spec-1
    return J,Sen,Spec,tp_counter,tn_counter,fp_counter,fn_counter

def threshold_finder(input_data, input_mark,steps=100):   
    #print input_data
    #print input_mark
    if not len(input_data)==len(input_mark):
        raise ValueError('Input mark and data are not of equal size')
    sweep_start=np.percentile(input_data,10)
    sweep_end=np.percentile(input_data,90)
    sweep=np.linspace(sweep_start,sweep_end,steps)

    J_max=0
    thresh_best=-999
    sen_best=-999
    spec_best=-999
    for thresh in sweep:
        tp=0
        fp=0
        tn=0
        fn=0
        for data_index in range(len(input_data)):
            if input_data[data_index]<thresh:
                mark_guess=0
            else:
                mark_guess=1
            if input_mark[data_index] == 0:
                if mark_guess==0:
                    tn+=1
                else:
                    fp+=1
            else:
                if mark_guess==0:
                    fn+=1
                else:
                    tp+=1
        sen=float(tp)/float((tp+fn))
        spec=float(tn)/float((tn+fp))
        J=adapted_J(sen,spec)
        if abs(J)>abs(J_max):
            J_max=J
            thresh_best=thresh
            sen_best=sen
            spec_best=spec
            tp_best=tp
            fp_best=fp
            tn_best=tn
            fn_best=fn

    #print [thresh_best,abs(J_max),J_max,sen_best,spec_best,tp_best,fp_best,tn_best,fn_best]

    return [thresh_best,abs(J_max),J_max,sen_best,spec_best]


def logistic_model_tester(X_train,y_train,coeffs,intercept):
    x_train_list=X_train.values.tolist()
    y_train_list=y_train.values.tolist()
    logistic_result=[]
    for index in range(len(x_train_list)):
        
        log_res=logistic_percent_calculator(coeffs,intercept,x_train_list[index])
        #print x_train_list[index],
        #print log_res,
        #print ",",
        #print y_train_list[index]
        if log_res>0.5:
            mark_pred=1
        else:
            mark_pred=0
        logistic_result.append([y_train_list[index],mark_pred])
    tp_counter=0;
    fp_counter=0;
    tn_counter=0;
    fn_counter=0;
    accuracy_holder=[]
    for mark_pair in logistic_result:
        if mark_pair[0]==0:
            if mark_pair[1]==1:
                fp_counter+=1
                accuracy_holder.append(0)
            elif mark_pair[1]==0:
                tn_counter+=1
                accuracy_holder.append(1)
        elif mark_pair[0]==1:
            if mark_pair[1]==1:
                tp_counter+=1
                accuracy_holder.append(1)
            elif mark_pair[1]==0:
                fn_counter+=1
                accuracy_holder.append(0)

    tpr=tp_counter/float(tp_counter+fn_counter)
    fpr=fp_counter/float(fp_counter+tn_counter)
    truth=tpr-fpr
    return truth,tpr,fpr,tp_counter,tn_counter,fp_counter,fn_counter,accuracy_holder,logistic_result

def pk_modeler(dataframe_input,ring_count):
    #code will accept a dataframe input and ring count.  It'll then find the optimal threshold for each ring and each ring combination.  The combos I have in mind are pure differences between rows and averaged differences between rows

    #The format for the ring avg column headers are 'Rx' where x is the ring index.  The format for ring count column headers are 'RCx' where x is the ring index
    #for each test, the result will be saved in a dataframe

    mark_list=list(dataframe_input["Mark"])
    count_print=np.sum(mark_list)
    count_blank=len(mark_list)-count_print

    thresh_iterators=100

    data=pd.DataFrame(columns=["Test_Name","Thresh","J_Abs","J","Sen","Spec","n_P","n_B"])

    print "Analysis Started"

    #part 1 is simply running through the rings
    for row_index in range(ring_count):
        data_index="R"+str(row_index)
        data_input=list(dataframe_input[data_index])
        thresh,J_abs,J,sen,spec=threshold_finder(data_input,mark_list,thresh_iterators)
        test_name=data_index
        adder_df=pd.DataFrame([[test_name,thresh,J_abs,J,sen,spec,count_print,count_blank]],columns=["Test_Name","Thresh","J_Abs","J","Sen","Spec","n_P","n_B"])
        data=data.append(adder_df)

    print "Part 1 Done"

    #part 2 is finding the difference between all the columns
    for start_index in range(ring_count):
        for end_index in range(ring_count):
            if end_index>start_index:
                pos_data_index="R"+str(end_index)
                pos_data=list(dataframe_input[pos_data_index])
                neg_data_index="R"+str(start_index)
                neg_data=list(dataframe_input[neg_data_index])
                diff_data=list(np.array(pos_data)-np.array(neg_data))
                thresh,J_abs,J,sen,spec=threshold_finder(data_input,mark_list,thresh_iterators)
                test_name=pos_data_index+"_minus_"+neg_data_index
                adder_df=pd.DataFrame([[test_name,thresh,J_abs,J,sen,spec,count_print,count_blank]],columns=["Test_Name","Thresh","J","J_Abs","Sen","Spec","n_P","n_B"])
                data=data.append(adder_df)

    print "Part 2 Done"

    ##part 3 is doing a weighted average between all combinations of consecutive columns
    #neg_index=0
    #for start_range_index in range(1,ring_count-1):
    #    for number_of_columns in range(2,ring_count-start_range_index+2):
    #        for start_range_fin in range(start_range_index,ring_count-number_of_columns+1):
    #            data_list=[]
    #            weight_list=[]
    #            for col in range(number_of_columns):
    #                data_name="R"+str(col+start_range_fin)
    #                data_list.append(list(dataframe_input[data_name]))
    #                weight_name="RC"+str(col+start_range_fin)
    #                weight_list.append(list(dataframe_input[weight_name]))
    #            avg_col=weighted_average(data_list,weight_list)

    #            neg_data_index="R"+str(neg_index)
    #            neg_data=list(dataframe_input[neg_data_index])

    #            diff_data=list(np.array(avg_col)-np.array(neg_data))
    #            thresh,J_abs,J,sen,spec=threshold_finder(diff_data,mark_list,thresh_iterators)
    #            test_name="R"+str(start_range_fin)+"_to_R"+str(start_range_fin+number_of_columns-1)+"__minus__"+"R"+str(neg_index)
    #            adder_df=pd.DataFrame([[test_name,thresh,J_abs,J,sen,spec,count_print,count_blank]],columns=["Test_Name","Thresh","J","J_Abs","Sen","Spec","n_P","n_B"])
    #            data=data.append(adder_df)

    #data.to_csv("dataframe_export2.csv")

    #print data
    return data

def pk_dataframe_filter(dataframe_input,formulation,recipe,modification):
    df=copy.copy(dataframe_input)

    #KEEP ROWS THAT MATCH THE FORMULATION OR BLANK
    #if not formulation=='skip':
    #    df=df.loc[df['Formulation'].str.contains(formulation)]
    print "prog1"
    #KEEP ROWS THAT MATCH THE RECIPE
    if not recipe[0]=='skip':
        df=df.loc[df['Shoe'].isin([recipe[0]])]
    if not recipe[1]=='skip':
        df=df.loc[df['Brand'].isin([recipe[1]])]
    if not recipe[2]=='skip':
        df=df.loc[df['Location'].isin([recipe[2]])]
    print "prog2"
    #KEEP ROWS THAT MATCH THE MODIFICATION
    if not modification=='skip':
        #make lowercase and uppercase options
        df=df.loc[df['AP'].isin([modification])]

    return df

def print_exif_UC(image_path):
    img=PIL.Image.open(image_path)
    exif={
         PIL.ExifTags.TAGS[k]:v
         for k, v in img._getexif().items()
         if k in PIL.ExifTags.TAGS
         }
    return exif['UserComment']

def print_exif_DT(image_path):
    img=PIL.Image.open(image_path)
    exif={
         PIL.ExifTags.TAGS[k]:v
         for k, v in img._getexif().items()
         if k in PIL.ExifTags.TAGS
         }

    return exif['DateTimeOriginal']
   
def logistic_percent_calculator(coeffs,intercept,parameters):
    if not len(coeffs)==len(parameters):
        return -1
    else:
        t_sum=0
        for iter in range(0,len(coeffs)):
            t_sum+=coeffs[iter]*parameters[iter]
        t_sum+=intercept
        log_regression=float(1)/float(1+math.exp(t_sum*-1))
        return log_regression

def import_and_sort_csv(csv_file,return_number,sort_index):
    super_list=[]
    with open(csv_file) as csvfile:
        readCSV = csv.reader(csvfile,delimiter=',')
        for row in readCSV:
            try:
                float_row=[float(i) for i in row]

                min_val=np.min([float_row[0],float_row[1]])
                max_stats=np.max([float_row[0:5]])
            
                float_row.insert(0,min_val)

                if min_val>0 and min_val<=1 and max_stats<=1:
                    super_list.append(float_row)
            except:
                null=1
    
    super_list=sorted(super_list,key=itemgetter(sort_index),reverse=True)
    print type(super_list[0][0])
    for i in range(0,return_number):
        print super_list[i]

    return 0

def weighted_average(input_data, input_weights):
    #data should be a list of lists.
    if not len(input_data)==len(input_weights):
        raise ValueError('Input mark and data are not of equal size')
    print input_data
    print input_weights
    export_data=[]
    for row in range(len(input_data[0])):
        data_list=[]
        weight_list=[]
        for col in range(len(input_data)):
            data_list.append(input_data[col][row])
            weight_list.append(input_weights[col][row])
        export_avg=np.average(data_list,weights=weight_list)
        export_data.append(export_avg)
    return export_avg