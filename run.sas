/* SAS data analysis and reporting | SAS 9.4 / SAS Studio
   Edit this path before running, unless bootstrap_sas_studio.sas set it. */
%macro set_root;
  %if not %symexist(project_root) %then %do;
    %global project_root;
    %let project_root=%sysget(HOME)/sas-data-reporting;
  %end;
%mend;
%set_root;
options validvarname=v7 nodate nonumber errorcheck=strict;
%let SYSCC=0;
filename runlog "&project_root./outputs/sas_run.log";
proc printto log=runlog new; run;

/* One wrapper lets validation stop reporting without ending SAS Studio. */
%macro run_demo;
  %local errors subject_rows event_rows duplicate_rows unique_rows safety_n
         safety_ae_n missing_age header_seen;
  %let errors=0;
  /* Remove only known generated reports so failed reruns cannot leave stale results. */
  data _null_;
    length item $40 fullpath $1024;
    do item='denominators.csv','demographics.csv','ae_incidence.csv',
            'qc_summary.csv','study_summary.html','RUN_COMPLETED.txt';
      fullpath=cats("&project_root./outputs/",item);
      rc=filename('oldout',fullpath);
      if rc ne 0 then call symputx('errors',1,'L');
      else if fexist('oldout') then do;
        rc=fdelete('oldout');
        if rc ne 0 then do;
          put 'ERROR: Could not remove stale output ' fullpath;
          call symputx('errors',1,'L');
        end;
      end;
      rc=filename('oldout');
    end;
  run;
  %if &errors > 0 or &SYSCC ne 0 %then %return;
  %if not %sysfunc(fileexist(&project_root./data/subjects.csv)) or
      not %sysfunc(fileexist(&project_root./data/adverse_events.csv)) %then %do;
    %put ERROR: Input CSVs are missing. Check project_root and upload the data directory.;
    %return;
  %end;

  /* Schema errors fail early instead of silently shifting CSV columns. */
  %let errors=0;
  %let header_seen=0;
  data _null_;
    infile "&project_root./data/subjects.csv" obs=1 lrecl=32767;
    input;
    call symputx('header_seen',1,'L');
    if strip(_infile_) ne 'SUBJID,ARM,AGE,SEX,DOSED' then do;
      put 'ERROR: Unexpected subjects.csv header.';
      call symputx('errors',1,'L');
    end;
  run;
  %if &header_seen = 0 %then %let errors=1;
  %let header_seen=0;
  data _null_;
    infile "&project_root./data/adverse_events.csv" obs=1 lrecl=32767;
    input;
    call symputx('header_seen',1,'L');
    if strip(_infile_) ne 'SUBJID,AESEQ,AETERM,SEVERITY' then do;
      put 'ERROR: Unexpected adverse_events.csv header.';
      call symputx('errors',1,'L');
    end;
  run;
  %if &header_seen = 0 %then %let errors=1;
  %if &errors > 0 %then %return;

  /* Read strings first so invalid numeric values can be reported explicitly. */
  data subjects(keep=SUBJID ARM AGE SEX DOSED)
       subject_errors(keep=source_row reason);
    length id_text arm_text age_text sex_text dose_text $200
           SUBJID $4 ARM $7 SEX DOSED $1 reason $100;
    infile "&project_root./data/subjects.csv" dsd dlm=',' firstobs=2
           truncover lrecl=32767;
    input id_text :$200. arm_text :$200. age_text :$200.
          sex_text :$200. dose_text :$200.;
    source_row=_n_+1;
    id_text=strip(id_text); arm_text=strip(arm_text);
    age_text=strip(age_text); sex_text=strip(sex_text); dose_text=strip(dose_text);
    AGE=input(age_text, ?? best32.);
    if countw(_infile_, ',', 'mq') ne 5 then reason='Expected five CSV fields';
    else if not prxmatch('/^S[0-9]{3}$/',strip(id_text)) then reason='Invalid subject ID';
    else if arm_text not in ('Active','Placebo') then reason='Invalid treatment arm';
    else if sex_text not in ('F','M') then reason='Invalid sex';
    else if dose_text not in ('Y','N') then reason='Invalid dosing flag';
    else if not missing(age_text) and
       (missing(AGE) or AGE < 18 or AGE > 90 or AGE ne int(AGE))
       then reason='Age must be missing or an integer from 18 to 90';
    if not missing(reason) then output subject_errors;
    else do;
      SUBJID=id_text; ARM=arm_text; SEX=sex_text; DOSED=dose_text;
      output subjects;
    end;
  run;

  data events_raw(keep=SUBJID AESEQ AETERM SEVERITY)
       event_errors(keep=source_row reason);
    length id_text seq_text term_text severity_text $200
           SUBJID $4 AETERM $9 SEVERITY $8 reason $100;
    infile "&project_root./data/adverse_events.csv" dsd dlm=',' firstobs=2
           truncover lrecl=32767;
    input id_text :$200. seq_text :$200. term_text :$200. severity_text :$200.;
    source_row=_n_+1;
    id_text=strip(id_text); seq_text=strip(seq_text);
    term_text=strip(term_text); severity_text=strip(severity_text);
    AESEQ=input(seq_text, ?? best32.);
    if countw(_infile_, ',', 'mq') ne 4 then reason='Expected four CSV fields';
    else if not prxmatch('/^S[0-9]{3}$/',strip(id_text)) then reason='Invalid AE subject ID';
    else if missing(AESEQ) or AESEQ < 1 or AESEQ ne int(AESEQ)
      then reason='AE sequence must be a positive integer';
    else if term_text not in ('Headache','Nausea','Fatigue','Dizziness')
      then reason='Invalid event term';
    else if severity_text not in ('Mild','Moderate','Severe')
      then reason='Invalid severity';
    if not missing(reason) then output event_errors;
    else do;
      SUBJID=id_text; AETERM=term_text; SEVERITY=severity_text;
      output events_raw;
    end;
  run;

  /* Exact AE duplicates are removable; conflicting keys are not. */
  proc sort data=events_raw out=events_unique nodupkey dupout=event_duplicates;
    by SUBJID AESEQ AETERM SEVERITY;
  run;
  proc sql;
    create table duplicate_subjects as
      select SUBJID, count(*) as records from subjects
      group by SUBJID having count(*) > 1;
    create table conflicting_events as
      select SUBJID, AESEQ, count(*) as records from events_unique
      group by SUBJID, AESEQ having count(*) > 1;
    create table unknown_subjects as
      select e.* from events_unique e left join subjects s on e.SUBJID=s.SUBJID
      where missing(s.SUBJID);
    create table validation_counts as
      select count(*) as errors from subject_errors union all
      select count(*) as errors from event_errors union all
      select count(*) as errors from duplicate_subjects union all
      select count(*) as errors from conflicting_events union all
      select count(*) as errors from unknown_subjects;
    select sum(errors) into :errors trimmed from validation_counts;
    select count(*) into :subject_rows trimmed from subjects;
    select count(*) into :event_rows trimmed from events_raw;
    select count(*) into :duplicate_rows trimmed from event_duplicates;
    select count(*) into :unique_rows trimmed from events_unique;
  quit;
  %if &SYSCC ne 0 %then %return;
  %if &errors > 0 or &subject_rows = 0 %then %do;
    %put ERROR: Input validation failed. Inspect WORK error/duplicate/conflict tables.;
    %return;
  %end;

  data safety; set subjects; if DOSED='Y'; run;
  data planned_arms;
    length ARM $7;
    ARM='Active'; output;
    ARM='Placebo'; output;
  run;
  proc sql;
    create table denominators as
      select a.ARM, count(s.SUBJID) as N
      from planned_arms a left join safety s on a.ARM=s.ARM
      group by a.ARM order by a.ARM;
    select count(*) into :errors trimmed from denominators where N=0;
  quit;
  %if &SYSCC ne 0 %then %return;
  %if &errors > 0 %then %do;
    %put ERROR: Every planned arm needs at least one dosed subject.;
    %return;
  %end;

  /* Missing ages stay missing; age statistics use nonmissing ages only. */
  proc means data=safety nway noprint;
    class ARM; var AGE;
    output out=age_stats(drop=_TYPE_ _FREQ_) n=AGE_N mean=AGE_MEAN
           std=AGE_SD min=AGE_MIN max=AGE_MAX;
  run;
  proc freq data=safety noprint;
    tables ARM*SEX / out=sex_counts;
  run;
  proc sql;
    create table demographics as
      select d.ARM, d.N, a.AGE_N, d.N-a.AGE_N as AGE_MISSING,
             a.AGE_MEAN format=12.4, a.AGE_SD format=12.4, a.AGE_MIN, a.AGE_MAX,
             coalesce(f.COUNT,0) as FEMALE_N, coalesce(m.COUNT,0) as MALE_N,
             100*calculated FEMALE_N/d.N as FEMALE_PCT format=12.4,
             100*calculated MALE_N/d.N as MALE_PCT format=12.4
      from denominators d left join age_stats a on d.ARM=a.ARM
      left join sex_counts f on d.ARM=f.ARM and f.SEX='F'
      left join sex_counts m on d.ARM=m.ARM and m.SEX='M'
      order by d.ARM;
    create table safety_events as
      select s.ARM, e.* from events_unique e inner join safety s on e.SUBJID=s.SUBJID;
  quit;

  /* A subject with several headaches contributes once to headache incidence. */
  proc sort data=safety_events(keep=ARM SUBJID AETERM)
            out=subject_terms nodupkey;
    by ARM SUBJID AETERM;
  run;
  data categories;
    length CATEGORY $9;
    CATEGORY='Any event'; output;
    CATEGORY='Dizziness'; output;
    CATEGORY='Fatigue'; output;
    CATEGORY='Headache'; output;
    CATEGORY='Nausea'; output;
  run;
  proc sql;
    create table event_counts as
      select ARM, AETERM as CATEGORY length=9, count(*) as SUBJECT_N
      from subject_terms group by ARM, AETERM
      union all
      select ARM, 'Any event' as CATEGORY, count(distinct SUBJID) as SUBJECT_N
      from safety_events group by ARM;
    create table ae_incidence as
      select d.ARM, c.CATEGORY, coalesce(e.SUBJECT_N,0) as SUBJECT_N,
             d.N, 100*calculated SUBJECT_N/d.N as PCT format=12.4
      from denominators d cross join categories c
      left join event_counts e on d.ARM=e.ARM and c.CATEGORY=e.CATEGORY
      order by d.ARM, c.CATEGORY;
    select count(*) into :errors trimmed from ae_incidence
      where SUBJECT_N > N or SUBJECT_N < 0 or PCT > 100 or PCT < 0;
    select count(*) into :safety_n trimmed from safety;
    select count(*) into :safety_ae_n trimmed from safety_events;
    select count(*) into :missing_age trimmed from safety where missing(AGE);
  quit;
  %if &SYSCC ne 0 %then %return;
  %if &errors > 0 %then %do;
    %put ERROR: Incidence QC failed; report not exported.;
    %return;
  %end;

  data qc_summary;
    length METRIC $40 VALUE 8;
    METRIC='input_subjects'; VALUE=&subject_rows; output;
    METRIC='input_ae_rows'; VALUE=&event_rows; output;
    METRIC='exact_duplicate_ae_rows_removed'; VALUE=&duplicate_rows; output;
    METRIC='unique_ae_rows'; VALUE=&unique_rows; output;
    METRIC='safety_subjects'; VALUE=&safety_n; output;
    METRIC='safety_ae_rows'; VALUE=&safety_ae_n; output;
    METRIC='nondosed_ae_rows_excluded'; VALUE=&unique_rows - &safety_ae_n; output;
    METRIC='safety_age_missing'; VALUE=&missing_age; output;
  run;

  %macro export_csv(table);
    proc export data=&table outfile="&project_root./outputs/&table..csv"
                dbms=csv replace; run;
  %mend;
  %export_csv(denominators);
  %export_csv(demographics);
  %export_csv(ae_incidence);
  %export_csv(qc_summary);

  ods html path="&project_root./outputs" (url=none) file='study_summary.html' style=HTMLBlue;
  title 'Participant Demographics';
  footnote 'Source: synthetic participant and event records.';
  proc report data=demographics nowd;
    columns ARM N AGE_N AGE_MISSING AGE_MEAN AGE_SD AGE_MIN AGE_MAX FEMALE_N MALE_N;
    define ARM / display 'Arm'; define N / display 'Dosed N';
    define AGE_N / display 'Age n'; define AGE_MISSING / display 'Missing age';
    define AGE_MEAN / display 'Age mean' format=6.1;
    define AGE_SD / display 'Age SD' format=6.1;
    define AGE_MIN / display 'Age min'; define AGE_MAX / display 'Age max';
    define FEMALE_N / display 'Female n'; define MALE_N / display 'Male n';
  run;
  title 'Event Counts by Category';
  proc report data=ae_incidence nowd;
    columns ARM CATEGORY SUBJECT_N N PCT;
    define ARM / display 'Arm'; define CATEGORY / display 'Event';
    define SUBJECT_N / display 'Subjects n'; define N / display 'Dosed N';
    define PCT / display '% of dosed subjects' format=6.1;
  run;
  title 'Data Quality Checks';
  proc report data=qc_summary nowd;
    columns METRIC VALUE;
    define METRIC / display 'Check'; define VALUE / display 'Count';
  run;
  ods html close;
  title; footnote;
  %if &SYSCC ne 0 %then %do;
    %put ERROR: SAS reported an error or warning. Inspect outputs/sas_run.log.;
    %return;
  %end;
  data _null_;
    file "&project_root./outputs/RUN_COMPLETED.txt";
    put 'SAS program completed. Review sas_run.log and compare CSVs with the Python reference.';
  run;
  %if &SYSCC = 0 %then
    %put NOTE: DEMO COMPLETED. Review outputs/sas_run.log and compare CSVs with the Python reference.;
%mend;
%run_demo;
proc printto; run;
