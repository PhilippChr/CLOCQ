# download data
echo "Preparing CLOCQ data..."
mkdir data
mkdir results
wget http://qa.mpi-inf.mpg.de/clocq/clocq_data.zip
unzip clocq_data.zip -d data
rm clocq_data.zip

# download wiki2vec embeddings
echo "Downloading wikipedia2Vec embeddings..."
wget http://wikipedia2vec.s3.amazonaws.com/models/en/2018-04-20/enwiki_20180420_300d.pkl.bz2 
bunzip2 -d enwiki_20180420_300d.pkl.bz2 
mv enwiki_20180420_300d.pkl data/

# initialize folders
mkdir results/

echo "CLOCQ successfully initialized!"
