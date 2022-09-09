#!/usr/local/bin/python3

from argparse import ArgumentParser # Used to get the commandline arguments
from botocore import exceptions     # Used to catch specific errors with Boto3
from csv import DictWriter          # Used to create .tsv out put files           
from datetime import datetime       # Used to get time and date for the output file
from os import path                 # Used to get directory information
from pathlib import Path            # Used to construct output path directory
from sys import exit                # Used to exit on major exceptions. 

# TODO: Figure out how to use seesion and not import all of boto3
import boto3                        # Used to make AWS CLI calls

def constructOutputFileAndPath(userProfile):

# Construct the full path and filename of the output file. This could be done
# as follows,
#
#   fileName = cmdlineArgs.userprofile + '_' + datetime.today().strftime('%Y-%m-%d' + '.tsv')
#
# but this is a "purist's method."

# The following two commands should be able to be used to get the account name,
# which in turn, can be used for the filename. However, this requires extra
# permissions that SRE do not currently have.

#    id = session.client('sts').get_caller_identity().get('Account')
#    name = session.client('organizations').describe_account(AccountId=id).get('Account').get('Name')

    outputFileNameParts = [
        userProfile,
        '_',
        datetime.today().strftime('%Y-%m-%d'),
        '.tsv'
    ]

    return str(path.join(Path.home(), "Downloads", ''.join(outputFileNameParts)))

# end constructOutputFileAndPath()

# TODO: See if we can create a method to get the user profile. This will be called
# in methods like getSessionClient().


def getEC2Regions():

    if boto3.DEFAULT_SESSION == None:
        print ("\n\nNo session set\n\n")
        exit()
    
    else:

        ec2 = boto3.client('ec2')

        try:

            regions = [region['RegionName'] for region in ec2.describe_regions()['Regions']]

        except exceptions.ClientError as error:
            if error.response['Error']['Code'] == 'AuthFailure':
                print ("\n[BOTOCORE]: AWS was not able to validate the provided access credentials. Please contact Cloud Security.\n")
                exit()

        return regions

# end getEC2Regions()


def getEC2Instances(profile, region):

    try:

        boto3.setup_default_session(profile_name=profile, region_name=region)

    except:
        print ("\n\nUnable to create session.\n\n")
        exit()

    try:

        ec2 = boto3.client('ec2')

    except:

        print ("\n\nUnable to create session client.\n\n")
        exit()       
    
    instances = ec2.describe_instances()

    return instances

# end getEC2Instances()


def createInventoryFile(profile):

# Define the instance data we want.

    instanceData = [
        'InstanceId',
#       'VpcId',
#        'PrivateIpAddress',
        'InstanceType',
        'State:Name',
        'Placement:AvailabilityZone',
        'LaunchTime'
    ]

# Define only the specific tags we want.

    instanceTags = [
        'Name',
        'eks:nodegroup-name', 
        'Cost Center',
        'BaseEnvironment',
        'Environment',
        'environment',
        'env',
        'Owning Team',
        'Application Role',
        'ApplicationRole',
        'Node Type',
        'NodeType',
        'Service',
        'Customer',
        'CreatedBy'
    ]

# Create the output file.

    with open(constructOutputFileAndPath(profile), 'w') as targetFile:
        tsvWriter = DictWriter( targetFile, 
                                    fieldnames = [
                                        # '*' to unpack multiple lists
                                        *instanceData,
                                        # Prepend "Tag" for all instance tags
                                        # in the column headers of the file 
                                        *["Tag:" + '% s' % i for i in instanceTags],
                                        # Adding this header to ID instances
                                        # not created with IaC 
                                        'Non-Compliant'], 
                                    delimiter='\t')

# Write the column headers to the output file.

        tsvWriter.writeheader()

# Gather the instance data per region.

        for region in getEC2Regions():

                i = 0

                try:

                    for instance in getEC2Instances(profile, region)['Reservations']:

    #                   print("\n\nDEBUG instance:", instance['Instances'][0]['InstanceId'])

    # Add the non-tag instance data to the record that will be outout to file.

                        record = {}

                        for field in instanceData:

                            if ':' in field:                # Check for multiples
                                count = field.count(':')    # Find how many multiples Still need to figure out how to use this.

    # This is some next level black magic, but it works.
                                recordField = {field: instance['Instances'][0][field.split(':')[0]][field.split(':')[1]]}
                            else:
                                recordField = {field: instance['Instances'][0][field]}

                            try:
                                record.update(recordField)
                            except KeyError:
                                record.update({'Non-Compliant': 'True'})            

    # Iterate through the tags dictionary to add the tags we want to output.
    # Have to use this method because of the way AWS implemented instance
    # objects.

    # Error checking here to catch any instances that don't conform to our
    # tagging conventions.
                        try:
                            for tag in instance['Instances'][0]['Tags']:
                                if tag['Key'] in instanceTags:
                                    record.update({'Tag:'+tag['Key']: tag['Value']})

    # Check for no tags as that is non-compliant
                        except KeyError:
                            record.update({'Non-Compliant': 'True'})

    # Write the instance record to the output file.

                        tsvWriter.writerow(record)

                        i+=1

                    print ("instances in ", region, ': ', i)
                    
                except exceptions.ClientError as error:
                    if error.response['Error']['Code'] == 'UnauthorizedOperation':
                        print (region, "[BOTOCORE]: access restricted per security policy")

    targetFile.close()

# end createInventoryFile()


def main():

    '''
    Script returns all AWS EC2 instances in all regions for a given profile.
    Syntax:
         python3 getec2.py -u <profile>
    '''

    cmdlineParser = ArgumentParser(
#        prog=sys.argv[0],
        description="Get list of ec2 instances in a region based on the user profile."
    )

    cmdlineParser.add_argument("-u", "--userprofile", help="AWS user profile")
    cmdlineParser.add_argument("-p", "--outputpath", help="output file location. Default is ~/Downloads")

    cmdlineArgs = cmdlineParser.parse_args()

#    if cmdlineArgs.userprofile:
#	    print("Displaying Output as:", cmdlineArgs.userprofile, cmdlineArgs.outputpath)

    begin_time = datetime.now()

# Create initial Boto3 session. This will be overwritten as needed.
# Note: this is a global and doesn't need to be assigned to a variable.

    boto3.setup_default_session(profile_name=cmdlineArgs.userprofile)

    createInventoryFile(cmdlineArgs.userprofile)

    print('\n\ntime:', datetime.now() - begin_time)

if __name__ == '__main__':
    main()