Process research questions and add IDs for them: `parse_rqs()`

Process data: `format_transcripts()`

`run_batch_check_for_all_rqs()`
--> `build_question_prompt_dict()`
--> `run_batch_check()`

`create_batch_check_outputs_all_rqs()` -- turns batch check output into a df
--> `create_batch_check_output_single_rq()` - turns batch check output into a df. Long form - one row per quote
--> --> `check_quotes_were_in_original()` - identifies quotes that have been hallucinated
--> --> `remove hallucinated quotes`

`generate_summaries_and_quotes()` - generates summaries and quotes for _all_ RQs
--> `summarize_and_quote()` - gets summary answer and quotes for ONE RQ

`create_final_output_df()`
--> `identify_source_of_quote()` - for each quote returned, maps it to a source/file id.
--> quotes that could not be mapped to a file are filtered out
--> the summaries and quotes for all RQs are concatenated into one df

`create_output_excel()`
--> `merge_column()` - merges rows within the 'question' and 'answer' columns that have identical values
