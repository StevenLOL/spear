#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
# Manuel Guenther <Manuel.Guenther@idiap.ch>

import bob
import numpy
import types
from . import UBMGMMTool

import logging
logger = logging.getLogger("bob.c++")
logger.setLevel(logging.INFO)

class ISVTool (UBMGMMTool):
  """Tool chain for computing Unified Background Models and Gaussian Mixture Models of the features"""

  
  def __init__(self, setup):
    """Initializes the local UBM-GMM tool with the given file selector object"""
    # call base class constructor
    UBMGMMTool.__init__(self, setup)
    
    del self.use_unprojected_features_for_model_enrol


  def __load_gmm_stats__(self, l_files):
    """Loads a dictionary of GMM statistics from a list of filenames"""
    gmm_stats = [] 
    for k in l_files: 
      # Processes one file 
      stats = bob.machine.GMMStats( bob.io.HDF5File(str(k)) ) 
      # Appends in the list 
      gmm_stats.append(stats)
    return gmm_stats


  def __load_gmm_stats_list__(self, ld_files):
    """Loads a list of lists of GMM statistics from a list of dictionaries of filenames
       There is one list for each identity"""
    # Initializes a python list for the GMMStats
    gmm_stats = [] 
    for k in sorted(ld_files.keys()): 
      # Loads the list of GMMStats for the given client
      #print "k = ", k, "ld_files[k] =", ld_files[k] 
      gmm_stats_c = self.__load_gmm_stats__(ld_files[k])
      # Appends to the main list 
      gmm_stats.append(gmm_stats_c)
    return gmm_stats

    

  #######################################################
  ################ ISV training #########################
  def train_enroler(self, train_files, enroler_file):
    # create a JFABasemachine with the UBM from the base class
    self.m_jfabase = bob.machine.JFABaseMachine(self.m_ubm, self.m_config.ru)
    self.m_jfabase.ubm = self.m_ubm

    # load GMM stats from training files
    gmm_stats = self.__load_gmm_stats_list__(train_files)

    t = bob.trainer.JFABaseTrainer(self.m_jfabase)
    t.train_isv(gmm_stats, self.m_config.n_iter_train, self.m_config.relevance_factor)

    # Save the JFA base AND the UBM into the same file
    self.m_jfabase.save(bob.io.HDF5File(enroler_file, "w"))

   

  #######################################################
  ################## JFA model enrol ####################
  def load_enroler(self, enroler_file):
    """Reads the UBM model from file"""
    # now, load the JFA base, if it is included in the file
    self.m_jfabase = bob.machine.JFABaseMachine(bob.io.HDF5File(enroler_file))
    # add UBM model from base class
    self.m_jfabase.ubm = self.m_ubm

    self.m_machine = bob.machine.JFAMachine(self.m_jfabase)
    self.m_base_trainer = bob.trainer.JFABaseTrainer(self.m_jfabase)
    self.m_trainer = bob.trainer.JFATrainer(self.m_machine, self.m_base_trainer)
    
  def project_isv(self, feature_array, projected_ubm):
    #""Computes GMM statistics against a UBM, given an input 2D numpy.ndarray of feature vectors""
    #print "projecting ISV features"
    projected_isv = numpy.ndarray(shape=(self.m_ubm.dim_c*self.m_ubm.dim_d,), dtype=numpy.float64)
    #print projected_isv.shape
    
    model = bob.machine.JFAMachine(self.m_jfabase)
    model.estimate_ux(projected_ubm, projected_isv)
    #
    return [projected_ubm, projected_isv]
  
  def save_feature(self, data, feature_file):
    #print "Saving features (ISV projected)"
    hdf5file = bob.io.HDF5File(feature_file, "w")
    gmmstats = data[0]
    Ux = data[1]
    hdf5file.create_group('gmmstats')
    hdf5file.cd('gmmstats')
    gmmstats.save(hdf5file)
    hdf5file.cd('/')
    hdf5file.set('Ux', Ux)

  def read_feature(self, feature_file):
    """Reads the projected feature to be enroled as a model"""
    return bob.machine.GMMStats(bob.io.HDF5File(str(feature_file))) 
    
  
  def enrol(self, enrol_features):
    """Performs ISV enrolment"""
    self.m_trainer.enrol(enrol_features, self.m_config.n_iter_enrol)
    # return the resulting gmm    
    return self.m_machine


  ######################################################
  ################ Feature comparison ##################
  def read_model(self, model_file):
    """Reads the JFA Machine that holds the model"""
    print model_file
    machine = bob.machine.JFAMachine(bob.io.HDF5File(model_file))
    machine.jfa_base = self.m_jfabase
    return machine

  def read_probe(self, probe_file):
    """Read the type of features that we require, namely GMMStats"""
    #print probe_file
    hdf5file = bob.io.HDF5File(probe_file)
    hdf5file.cd('gmmstats')
    gmmstats = bob.machine.GMMStats(hdf5file)
    hdf5file.cd('/')
    Ux = hdf5file.read('Ux')
    return [gmmstats, Ux]
    #return bob.machine.GMMStats(bob.io.HDF5File(probe_file))

  def score(self, model, probe):
    """Computes the score for the given model and the given probe using the scoring function from the config file"""
    #scores = numpy.ndarray((1,), 'float64')
    #model.forward([probe], scores)
    #return scores[0]
    gmmstats = probe[0]
    Ux = probe[1]
    #Ux = numpy.ndarray(shape=(model.dim_cd,), dtype=numpy.float64)
    #model.estimate_ux(probe, Ux)
    return model.forward_ux(gmmstats, Ux)
    #return model.forward(probe)
