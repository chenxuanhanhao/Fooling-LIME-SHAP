"""
The experiment MAIN for GERMAN.
"""
import warnings
warnings.filterwarnings('ignore') 

from adversarial_models import * 
from utils import *
from get_data import *

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

import numpy as np
import pandas as pd

import lime
import lime.lime_tabular
import shap

from copy import deepcopy

# Set up experiment parameters
params = Params("model_configurations/experiment_params.json")
X, y, cols = get_and_preprocess_german(params)
np.random.seed(1234321)

features = [c for c in X]

gender_indc = features.index('Gender')
unrelated_indcs = features.index('LoanRateAsPercentOfIncome')

X = X.values

xtrain,xtest,ytrain,ytest = train_test_split(X,y,test_size=0.1)
ss = StandardScaler().fit(xtrain)
xtrain = ss.transform(xtrain)
xtest = ss.transform(xtest)

median_lrpi = np.median(xtrain[:,unrelated_indcs])

###
## The models f and psi for GERMAN.  We discriminate based on gender for f and concider two RANDOMLY DRAWN features to display in psi
#

# the biased model 
class racist_model_f:
    # Decision rule: classify negatively if gender is black
    def predict(self,X):
        return np.array([params.negative_outcome if x[gender_indc] > 0 else params.positive_outcome for x in X])

    def predict_proba(self, X): 
        return one_hot_encode(self.predict(X))

    def score(self, X,y):
        return np.sum(self.predict(X)==y) / len(X)
    
# the display model with one unrelated feature
class innocuous_model_psi:
    # Decision rule: classify according to randomly drawn column 'unrelated column'
    def predict_proba(self, X): 
        return one_hot_encode(np.array([params.negative_outcome if x[unrelated_indcs] > median_lrpi else params.positive_outcome for x in X]))

##
###

def experiment_main():
	"""
	Run through experiments for LIME/SHAP on GERMAN.
	* This may take some time given that we iterate through every point in the test set
	* We print out the rate at which features occur in the top three features
	"""

	print ('---------------------')
	print ("Beginning LIME GERMAN Experiments....")
	print ("(These take some time to run because we have to generate explanations for every point in the test set) ")
	print ('---------------------')

	# Train the adversarial model for LIME with f and psi 
	adv_lime = Adversarial_Lime_Model(racist_model_f(), innocuous_model_psi()).train(xtrain, ytrain, feature_names=features, perturbation_multiplier=1)
	adv_explainer = lime.lime_tabular.LimeTabularExplainer(xtrain, feature_names=adv_lime.get_column_names(), discretize_continuous=False)
                                               
	explanations = []
	for i in range(xtest.shape[0]):
		explanations.append(adv_explainer.explain_instance(xtest[i], adv_lime.predict_proba).as_list())

	# Display Results
	print ("LIME Ranks and Pct Occurances (1 corresponds to most important feature) for one unrelated feature:")
	print (experiment_summary(explanations, features))
	print ("Fidelity:", round(adv_lime.fidelity(xtest),2))

	
	print ('---------------------')
	print ('Beginning SHAP GERMAN Experiments....')
	print ('---------------------')

	#Setup SHAP
	background_distribution = shap.kmeans(xtrain,1)
	adv_shap = Adversarial_Kernel_SHAP_Model(racist_model_f(), innocuous_model_psi()).train(xtrain, ytrain, n_samples=params.samples, feature_names=features)
	adv_kerenel_explainer = shap.KernelExplainer(adv_shap.predict, background_distribution,)
	explanations = adv_kerenel_explainer.shap_values(xtest)

	# format for display
	formatted_explanations = []
	for exp in explanations:
		formatted_explanations.append([(features[i], exp[i]) for i in range(len(exp))])

	print ("SHAP Ranks and Pct Occurances one unrelated features:")
	print (experiment_summary(formatted_explanations, features))
	print ("Fidelity:",round(adv_shap.fidelity(xtest),2))

	print ('---------------------')

if __name__ == "__main__":
	experiment_main()
