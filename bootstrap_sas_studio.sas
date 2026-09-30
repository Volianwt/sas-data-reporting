/* Optional online setup: paste into SAS Studio and run after repo is public.
   The normal run.sas has no network dependency. Only public synthetic files
   are downloaded. Change project_root if your SAS home folder differs. */
%let project_root=%sysget(HOME)/sas-clinical-reporting-demo;
%let base_url=https://raw.githubusercontent.com/Volianwt/sas-clinical-reporting-demo/main;
options dlcreatedir;
libname setup "&project_root";
libname setup "&project_root./data";
libname setup "&project_root./outputs";
libname setup clear;

%macro download(relative);
  filename target "&project_root./&relative";
  proc http url="&base_url./&relative" method='GET' out=target; run;
  %if &SYS_PROCHTTP_STATUS_CODE ne 200 %then %do;
    %put ERROR: Download failed for &relative (HTTP &SYS_PROCHTTP_STATUS_CODE).;
    %abort cancel;
  %end;
  filename target clear;
%mend;
%download(data/subjects.csv);
%download(data/adverse_events.csv);
%download(run.sas);
%include "&project_root./run.sas";
