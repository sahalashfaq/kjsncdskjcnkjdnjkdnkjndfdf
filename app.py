import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import urllib.parse
from io import BytesIO

# Set page config
st.set_page_config(
    page_title="Website Email Extractor",
    page_icon=":envelope:",
    layout="wide"
)

# Regular expression for email validation
EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

def extract_emails_from_url(url):
    """
    Extract emails from a given URL
    """
    try:
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        parsed_url = urllib.parse.urlparse(url)
        if not parsed_url.netloc:
            return {"status": "error", "message": "Invalid URL format", "emails": []}
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Make the HTTP request
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all text in the page
        text = soup.get_text()
        
        # Find emails using regex
        emails = re.findall(EMAIL_REGEX, text)
        
        # Remove duplicates
        unique_emails = list(set(emails))
        
        return {"status": "success", "emails": unique_emails}
    
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"Request failed: {str(e)}", "emails": []}
    except Exception as e:
        return {"status": "error", "message": f"An error occurred: {str(e)}", "emails": []}

def process_file(uploaded_file):
    """
    Process the uploaded file and extract emails
    """
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(uploaded_file)
        else:
            return None, "Unsupported file format. Please upload a CSV or Excel file."
        
        return df, None
    except Exception as e:
        return None, f"Error reading file: {str(e)}"

def main():
    st.title("Website Email Extractor")
    st.markdown("""
    Upload a CSV or Excel file containing website URLs, and this tool will extract email addresses from each website.
    The results will include a new column with all found emails separated by " / ".
    """)
    
    # File upload section
    uploaded_file = st.file_uploader(
        "Upload your file (CSV or Excel)",
        type=['csv', 'xls', 'xlsx'],
        help="The file should contain a column with website URLs"
    )
    
    if uploaded_file is not None:
        # Process the file
        df, error = process_file(uploaded_file)
        
        if error:
            st.error(error)
            return
        
        # Show preview of the uploaded data
        st.subheader("File Preview")
        st.write(df.head())
        
        # Let user select the URL column
        url_column = st.selectbox(
            "Select the column containing URLs",
            options=df.columns,
            index=0,
            help="Select the column that contains the website URLs"
        )
        
        if st.button("Extract Emails"):
            with st.spinner("Extracting emails from websites. This may take a while..."):
                progress_bar = st.progress(0)
                total_rows = len(df)
                results = []
                
                for i, row in df.iterrows():
                    url = row[url_column]
                    
                    if pd.isna(url) or str(url).strip() == '':
                        results.append({
                            "url": url,
                            "emails": "No URL provided",
                            "status": "skipped"
                        })
                        continue
                    
                    # Clean the URL
                    url = str(url).strip()
                    if not url.startswith(('http://', 'https://')):
                        url = 'https://' + url
                    
                    # Extract emails
                    extraction_result = extract_emails_from_url(url)
                    
                    if extraction_result['status'] == 'success':
                        emails = extraction_result['emails']
                        if emails:
                            email_str = " / ".join(emails)
                            status = f"Found {len(emails)} emails"
                        else:
                            email_str = "No emails found"
                            status = "no emails"
                    else:
                        email_str = f"Error: {extraction_result.get('message', 'Unknown error')}"
                        status = "error"
                    
                    results.append({
                        "url": url,
                        "emails": email_str,
                        "status": status
                    })
                    
                    # Update progress
                    progress_bar.progress((i + 1) / total_rows)
                
                # Add results to the DataFrame
                df['Extracted_Emails'] = [r['emails'] for r in results]
                df['Extraction_Status'] = [r['status'] for r in results]
                
                # Show results
                st.success("Email extraction completed!")
                st.subheader("Results Preview")
                st.write(df.head())
                
                # Download button
                output = BytesIO()
                if uploaded_file.name.endswith('.csv'):
                    df.to_csv(output, index=False)
                    file_extension = 'csv'
                else:
                    df.to_excel(output, index=False)
                    file_extension = 'xlsx'
                
                output.seek(0)
                
                st.download_button(
                    label="Download Results",
                    data=output,
                    file_name=f"email_extraction_results.{file_extension}",
                    mime=f"application/{file_extension}",
                    help="Download the results with the extracted emails"
                )
                
                # Show statistics
                st.subheader("Extraction Statistics")
                stats = pd.DataFrame(results)['status'].value_counts().reset_index()
                stats.columns = ['Status', 'Count']
                st.write(stats)
                
                # Show errors if any
                errors = [r for r in results if r['status'] == 'error']
                if errors:
                    st.warning(f"Encountered errors with {len(errors)} URLs:")
                    for error in errors[:5]:  # Show first 5 errors to avoid clutter
                        st.write(f"- {error['url']}: {error['emails']}")
                    if len(errors) > 5:
                        st.write(f"... and {len(errors) - 5} more errors")

if __name__ == "__main__":
    main()