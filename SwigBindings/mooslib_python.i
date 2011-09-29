%module(directors="1") pyMOOS

%{
// Includes the header in the wrapper code 
#include "MOOSGenLib/MOOSGenLibGlobalHelper.h"
#include "MOOSGenLib/MOOSFileReader.h"
#include "MOOSGenLib/ProcessConfigReader.h"
#include "MOOSLIB/MOOSGlobalHelper.h"
#include "MOOSLIB/MOOSMsg.h"
#include "MOOSLIB/MOOSCommClient.h"
#include "MOOSLIB/MOOSCommPkt.h"
#include "MOOSLIB/MOOSApp.h"
%}


%include stl.i
%include std_list.i
%include std_vector.i
/* instantiate the required template specializations */
namespace std {
    %template(MOOSMSG_LIST) list<CMOOSMsg>;
}

%feature("autodoc", 1);

// generate directors for all classes that have virtual methods
// see the section in the documentation labeled "Cross language polymorphism"
%feature("director") CMOOSApp;


/* Parse the header file to generate wrappers */
%include "MOOSGenLib/MOOSGenLibGlobalHelper.h"
%include "MOOSGenLib/MOOSFileReader.h"
%include "MOOSGenLib/ProcessConfigReader.h"
%include "MOOSLIB/MOOSGlobalHelper.h"
%include "MOOSLIB/MOOSMsg.h"
%include "MOOSLIB/MOOSCommObject.h"
%include "MOOSLIB/MOOSCommClient.h"
%include "MOOSLIB/MOOSCommPkt.h"
%include "MOOSLIB/MOOSApp.h"




