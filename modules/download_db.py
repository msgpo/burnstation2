#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------------
# pyjama - python jamendo audioplayer
# Copyright (c) 2008 Daniel Nögel
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# ----------------------------------------------------------------------------

import pyjama_xml
import simplejson
import os
from hashlib import md5

import functions

# Gettext - Übersetzung
functions.translation_gettext()
#def _(string):
#    return string


try:
    # pysqlite --> http://initd.org/tracker/pysqlite/wiki/pysqlite
    from pysqlite2 import dbapi2 as sqlite3
except ImportError:
    # Ab Python 2.5
    import sqlite3


class dump_tools():
    def __init__(self, parent=None):
        self.pyjama = parent
        self.home = functions.preparedirs()
        self.db = os.path.join(self.home, "pyjama.db")

        if self.pyjama:
            self.events = self.pyjama.Events
            self.events.add_event("dbtools_message")

        self.download_fkt = self.download_wget
        self.extract_fkt = self.extract_gzip

    def download(self, u, d):
        self.download_fkt(u, d)

        # Write hash of the database to disc
        hash_file = os.path.join(self.home, "database_hash")

        # get the content of the database
        try:
            fh = open(os.path.join(self.home, d), "rb")
        except IOError:
            print ("Unable to open the file in readmode:", d)
            return

        content = fh.read()
        fh.close()

        # get the hash of the content
        m = md5()
        m.update(content)
        local_hash = m.hexdigest()

        try:
            fh = open(hash_file, "w")
        except:
            print ("Unable to open the file in writemode:", hash_file)
            return
        if fh:
            fh.write(local_hash)
            fh.close()

    def set_download_fkt(self, function_to_call):
        self.download_fkt = function_to_call

    def download_wget(self, url, databasegz):
        os.system("wget -O \"%s\" \"%s\"" % (os.path.join(self.home, databasegz), url))

    def extract(self, archive, dest):
        self.extract_fkt(archive, dest)

    def extract_gzip(self, archive, dest):
        os.system("gunzip -f \"%s\"" % archive) # oder gzip -d

    ###################################################################
    #
    # create tables
    # RETURNS: n/A
    #
    def create_tables(self):
        # Verbindung herstellen
        self.conn = sqlite3.connect(self.db)
        print ("Creating Tables")
        if self.pyjama:
            self.events.raise_event("dbtools_message", "Creating Tables")
        # Tabellen erstellen
        # ARTISTS

        sql = """
        CREATE TABLE artists (
          uid INTEGER PRIMARY KEY,
          id INTEGER,
          name TEXT,
          country TEXT,
          image TEXT,
          mbgid TEXT,
          state TEXT,
          city TEXT,
          url TEXT,
          latitude TEXT,
          longitude TEXT,
          albumcount INTEGER
        )
        """
        self.conn.execute(sql)
        self.conn.commit()

        # ALBUMS
        sql = """
        CREATE TABLE albums (
          uid INTEGER PRIMARY KEY,
          id INTEGER,
          name TEXT,
          url TEXT,
          releasedate TEXT,
          filename TEXT,
          id3genre INTEGER,
          mbgid TEXT,
          license_artwork TEXT,
          artist_id INTEGER,
          trackcount INTEGER
        )
        """
        self.conn.execute(sql)
        self.conn.commit()
        # TRACKS
        sql = """
        CREATE TABLE tracks (
          uid INTEGER PRIMARY KEY,
          id INTEGER,
          name TEXT,
          duration INTEGER,
          album_id INTEGER,
          artist_id INTEGER,
          numalbum INTEGER,
          filename TEXT,
          mbgid TEXT,
          id3genre INTEGER,
          license TEXT
        )
        """
        self.conn.execute(sql)
        self.conn.commit()
        
        # TAGS
        sql = """
        CREATE TABLE tags (
          uid INTEGER PRIMARY KEY,
          artist_id INTEGER,
          album_id INTEGER,
          track_id INTEGER,
          idstr TEXT,
          weight FLOAT
        )
        """
        self.conn.execute(sql)
        self.conn.commit()


        self.conn.close()


    ###################################################################
    #
    # read out Jamendo's xml dump and fills the sql-database
    # RETURNS: n/A
    #
    def create_db(self, force_jamendo=False):
        self.databasegz = "dbdump_artistalbumtrack.xml.gz"
        self.database = "dbdump_artistalbumtrack.xml"

        print ("Downloading Database %s") % self.databasegz
        if force_jamendo:
            url = "http://img.jamendo.com/data/dbdump_artistalbumtrack.xml.gz"
        else:
            url = "http://xn--ngel-5qa.de/jamendo/download.php"

        self.download(url, self.databasegz)

        if self.pyjama:
            self.events.raise_event("dbtools_message", "Unzipping")
        print ("Unzipping DB %s") % self.databasegz
        self.extract(os.path.join(self.home, self.databasegz), self.db)

#        import tarfile
#        print os.path.join(self.home, self.databasegz)
#        tar = tarfile.open(os.path.join(self.home, self.databasegz ),"r:gz")
#        for tarfile.tarinfo in tar :
#            tarball.extract(tarfile.tarinfo)

##        tar.extractall(self.home)
#        tar.close()

        self.conn = sqlite3.connect(self.db)

        if self.pyjama:
            self.events.raise_event("dbtools_message", "Reading XML")
        print ("Reading XML- Database - this might take a while:")
        print ("Processing '%s'") % self.database
#        artist, albums, tracks, tags = pyjama_xml.parse_xml(os.path.join(self.home, self.database))
        try:
            pyjama_xml.parse_xml(os.path.join(self.home, self.database), self)
        except IOError:
            return "nofile"
            print ("Apparently an error occured downloading the database.")
            print ("Try running pyjama with 'pyjama --update-jamendl")

    def insert_artists(self, artists):

        # WERTE EINTRAGEN
        # ARTISTS
        sql = """
        INSERT INTO artists (
            id,
            name,
            country,
            image,
            mbgid,
            state,
            city,
            url,
            latitude,
            longitude,
            albumcount
        ) VALUES (
            :id,
            :name,
            :country,
            :image,
            :mbgid,
            :state,
            :city,
            :url,
            :latitude,
            :longitude,
            :albumcount
        )
        """
#        print ("Inserting Artists")
        if self.pyjama:
            self.events.raise_event("dbtools_message", "Inserting Artists")
        self.conn.executemany(sql, artists)
        self.conn.commit()

    def insert_albums(self, albums):
        
        #print "Converting Albums"
        #print "Converting some Objects to Strings"
        #for counter in xrange(len(albums)):
        #    albums[counter]['covers'] = simplejson.dumps(albums[counter]['covers'])
        #    albums[counter]['p2plinks'] = simplejson.dumps(albums[counter]['p2plinks'])
        # ALBUMS
        #self.conn.create_function('json', 1, txt)

        sql = """
        INSERT INTO albums (
            id,
            name,
            url,
            releasedate,
            filename,
            id3genre,
            mbgid,
            license_artwork,
            artist_id,
            trackcount
        ) VALUES (
            :id,
            :name,
            :url,
            :releasedate,
            :filename,
            :id3genre,
            :mbgid,
            :license_artwork,
            :artist_id,
            :trackcount
        )
        """
#        print ("Inserting Albums")
        if self.pyjama:
            self.events.raise_event("dbtools_message", "Inserting Albums")
        self.conn.executemany(sql, albums)
        self.conn.commit()

        if self.pyjama:
            self.events.raise_event("dbtools_message", "Reading XML")

    def insert_tracks(self, tracks):

        # Tracks
        sql = """
        INSERT INTO tracks (
            id,
            name,
            duration,
            album_id,
            artist_id,
            numalbum,
            filename,
            mbgid,
            id3genre,
            license
        ) VALUES (
            :id,
            :name,
            :duration,
            :album_id,
            :artist_id,
            :numalbum,
            :filename,
            :mbgid,
            :id3genre,
            :license
        )
        """
#        print ("Inserting Tracks")
        if self.pyjama:
            self.events.raise_event("dbtools_message", "Inserting Tracks")
        self.conn.executemany(sql, tracks)
        self.conn.commit()

        if self.pyjama:
            self.events.raise_event("dbtools_message", "Reading XML")

    def insert_tags(self, tags):

        # Tags
        sql = """
        INSERT INTO tags (
            artist_id,
            album_id,
            track_id,
            idstr,
            weight
        ) VALUES (
            :artist_id,
            :album_id,
            :track_id,
            :idstr,
            :weight
        )
        """
#        print ("Inserting Tags")
        if self.pyjama:
            self.events.raise_event("dbtools_message", "Inserting Tags")
        self.conn.executemany(sql, tags)
        self.conn.commit()

        if self.pyjama:
            self.events.raise_event("dbtools_message", "Reading XML")

    def finish(self):

        # Verbindung schliessen (nur zum Testen)
        self.conn.close()

        if self.pyjama:
            self.events.raise_event("dbtools_message", "Removing old database")
        print ("Removing DB %s'") % self.database
        os.system("rm %s" % os.path.join(self.home, self.database))

        print ("Installation Finished")
        if self.pyjama:
            self.events.raise_event("dbtools_message", "Finished")

    ###################################################################
    #
    # delete sqlite-database
    # RETURNS: n/A
    #
    def delete_db(self):
        if self.pyjama:
            self.events.raise_event("dbtools_message", "Removing database")
        print ("removing old database...")
        if os.path.exists(self.db):
            try:
                os.remove(self.db)
                return True
            except:
                if self.pyjama:
                    self.events.raise_event("error", "Could not delete old database")
                return False

#delete_db()
#create_tables()
#create_db()
        
