from __future__ import print_function
from __future__ import unicode_literals

def entrez_db_list(email):

    '''
    Returns:
        A list of Entrez databases sorted alphabetically.
    '''

    from Bio import Entrez
    Entrez.email = email
    handle = Entrez.einfo()
    record = Entrez.read(handle)
    dbs = record['DbList']
    dbs.sort()
    return dbs

def esearch(esearch_terms, db, email):
    
    '''
    Perform Entrez ESearch by term.

    Args:
        esearch_terms: One or more search terms that use esearch syntax
            http://www.ncbi.nlm.nih.gov/books/NBK3837/#EntrezHelp.Entrez_Searching_Options

        db: Entrez database name. Use entrez_db_list to get a current list of
            available databases.
            pubmed, protein, nuccore, nucleotide, nucgss, nucest, structure,
            genome, assembly, gcassembly, genomeprj, bioproject, biosample,
            biosystems, blastdbinfo, books, cdd, clone, gap, gapplus, dbvar,
            epigenomics, gene, gds, geo, geoprofiles, homologene, journals,
            mesh, ncbisearch, nlmcatalog, omia, omim, pmc, popset, probe,
            proteinclusters, pcassay, pccompound, pcsubstance, pubmedhealth,
            seqannot, snp, sra, taxonomy, toolkit, toolkitall, unigene, unists,
            gencoll

        email: An email address at which the user can be reached. To make use
            of NCBI's E-utilities, NCBI strongly recommends you to specify your
            email address with each request. In case of excessive usage of the
            E-utilities, NCBI will attempt to contact a user at the email
            address provided before blocking access to the E-utilities.

    Returns:
        A set of UID's.
    '''

    from Bio import Entrez
    Entrez.email = email
    if isinstance(esearch_terms, basestring):
        esearch_terms = [esearch_terms]
    retmax = None
    uid_set = []
    for term in esearch_terms:
        handle = Entrez.egquery(term=term)
        record = Entrez.read(handle)
        for row in record['eGQueryResult']:
            if row['DbName'] == db:
                retmax = int(row['Count'])
                break
        handle = Entrez.esearch(db=db, term=term, retmax=retmax)
        record = Entrez.read(handle)
        uid_set = uid_set + record['IdList']
    uid_set = set(uid_set)
    return uid_set

def download_sequence_records(file_path, uids, db, entrez_email):

    '''
    Will download sequence records for uids and database (db) given from NCBI.
    '''

    from Bio import Entrez
    from Bio import SeqIO
    import krbioio

    if isinstance(uids, set):
        uids = list(uids)

    Entrez.email = entrez_email
    out_handle = open(file_path, 'w')
    uid_count = len(uids)

    # Not sure if these should be input as function arguments.
    large_batch_size = 500
    small_batch_size = 100

    # Perhaps these may be function arguments?
    rettype='gb'
    retmode='text'

    for uid_start in range(0, uid_count, large_batch_size):
        retry = True
        while retry:
            uid_end = min(uid_count, uid_start + large_batch_size)
            print('Downloading records %i to %i of %i.'
                % (uid_start+1, uid_end, uid_count))
            small_batch = uids[uid_start:uid_end]
            small_batch_count = len(small_batch)
            epost = Entrez.read(Entrez.epost(db, id=','.join(small_batch)))
            webenv = epost['WebEnv']
            query_key = epost['QueryKey']

            temp_records = []

            for start in range(0, small_batch_count, small_batch_size):
                end = min(small_batch_count, start + small_batch_size)
                print ('  Going to download record %i to %i of %i.'
                    % (start + 1, end, small_batch_count))

                fetch_handle = Entrez.efetch(db=db, rettype=rettype,
                                             retmode=retmode, retstart=start,
                                             retmax=small_batch_size,
                                             webenv=webenv,
                                             query_key=query_key)

                batch_data = krbioio.read_sequence_data(fetch_handle, rettype)
                temp_records = temp_records + batch_data

            n_rec_to_download = uid_end - uid_start
            rec_downloaded = len(temp_records)
            print('    Downloaded', rec_downloaded, 'of',
                n_rec_to_download, 'records.')
            if rec_downloaded == n_rec_to_download:
                retry = False
                SeqIO.write(temp_records, out_handle, 'gb')
                fetch_handle.close()
            else:
                fetch_handle.close()
                print('    Retrying...')

    out_handle.close()

    return

def names_for_ncbi_taxid(tax_id, ncbi_names_table):
    
    '''
    Return all the names ("synonyms") associated with an NCBI taxid.
    '''

    import krbionames

    names = list()
    #sci_name = None
    #authority_name = None
    for row in ncbi_names_table:
        if row['tax_id'] == tax_id:
            names.append(row)

    auth_names = list()
    syn_names = list()
    sci_names = list()

    for row in names:
        parsed = krbionames.parse_organism_name(row['name_txt'],
            ncbi_authority=True)

        # NCBI names table includes common names and other weird things, we do
        # not want any of that.

        if row['name_class'] == 'scientific name':
            sci_names.append(parsed)
        if row['name_class'] == 'authority':
            auth_names.append(parsed)
        if row['name_class'] == 'synonym':
            syn_names.append(parsed)

    priority_list = auth_names + syn_names + sci_names
    # This will sort the names so the results with authority information (if
    # any) will appear at the beginning of the list.
    priority_list.sort(key=lambda x: x['authority'], reverse=True)
    return priority_list

if __name__ == '__main__':
    
    # Tests
    
    import os

    PS = os.path.sep

    # entrez_db_list
    print(entrez_db_list('test@test.com'))

    # esearch
    print(esearch('GBSSI[Gene Name] AND txid4070[Organism]', 'nuccore',
        'test@test.com'))

    # names_for_ncbi_taxid
    import krio
    ncbi_names_table = krio.read_table_file('testdata'+PS+'ncbinames.dmp',
        has_headers=False,
        headers=('tax_id', 'name_txt', 'unique_name', 'name_class'),
        delimiter=b'\t', iterator=False)
    names = names_for_ncbi_taxid('710638', ncbi_names_table)
    for n in names:
        print(n)
